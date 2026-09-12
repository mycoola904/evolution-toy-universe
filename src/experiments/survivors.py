from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from experiments.genomes import genome_display_digest, persisted_genome_key


@dataclass(frozen=True)
class Survivor:
    organism_id: int
    parent_organism_id: int | None
    age: int
    generation: int
    child_count: int
    final_energy: float
    birth_tick: int
    genome_id: str


@dataclass(frozen=True)
class SurvivorGenomeGroup:
    genome_id: str
    representative_organism_id: int
    survivor_count: int
    historical_organism_count: int
    survivor_percentage: float
    average_age: float
    oldest_age: int
    average_children: float
    maximum_children: int
    first_generation: int
    latest_generation: int
    survivors: tuple[Survivor, ...]


@dataclass(frozen=True)
class SurvivorFounderGroup:
    founder_organism_id: int
    survivor_count: int
    surviving_descendant_count: int
    total_descendants: int
    descendant_survivor_percentage: float
    distinct_survivor_genomes: int
    average_age: float
    oldest_age: int
    average_children: float
    maximum_children: int
    latest_generation: int
    founder_lifespan: int
    founder_alive_at_end: bool
    genomes: tuple[SurvivorGenomeGroup, ...]


@dataclass(frozen=True)
class SurvivorExplorer:
    founders: tuple[SurvivorFounderGroup, ...]

    @property
    def survivor_count(self) -> int:
        return sum(founder.survivor_count for founder in self.founders)


def build_survivor_explorer(
    rows: Iterable[Mapping[str, Any]],
) -> SurvivorExplorer:
    """Build the Founder -> Genome -> Survivor hierarchy for one run.

    A persisted null death tick is ETU's canonical alive-at-run-end marker.
    Genome membership is based on equality of the persisted JSON value; the
    digest is only a compact display label for that value.
    """
    organisms = {row["organism_id"]: row for row in rows}
    children_by_parent: dict[int, list[int]] = {}
    for row in organisms.values():
        parent_id = row["parent_organism_id"]
        if parent_id is not None:
            children_by_parent.setdefault(parent_id, []).append(
                row["organism_id"]
            )

    ancestry: dict[int, tuple[int, int] | None] = {}

    def resolve_ancestry(organism_id: int) -> tuple[int, int] | None:
        if organism_id in ancestry:
            return ancestry[organism_id]

        path: list[int] = []
        seen: set[int] = set()
        current_id = organism_id
        resolved: tuple[int, int] | None
        while True:
            if current_id in seen:
                raise ValueError("lineage contains a parent-child cycle")
            seen.add(current_id)
            if current_id in ancestry:
                resolved = ancestry[current_id]
                break
            current = organisms.get(current_id)
            if current is None:
                resolved = None
                break
            path.append(current_id)
            parent_id = current["parent_organism_id"]
            if parent_id is None:
                resolved = (
                    (current_id, 0)
                    if current["birth_tick"] == 0
                    else None
                )
                break
            current_id = parent_id

        for path_id in reversed(path):
            if resolved is None:
                ancestry[path_id] = None
            elif path_id == resolved[0]:
                ancestry[path_id] = resolved
            else:
                resolved = (resolved[0], resolved[1] + 1)
                ancestry[path_id] = resolved
        return ancestry.get(organism_id)

    family_rows: dict[int, list[Mapping[str, Any]]] = {}
    for row in organisms.values():
        resolved = resolve_ancestry(row["organism_id"])
        if resolved is not None:
            family_rows.setdefault(resolved[0], []).append(row)

    founder_groups = []
    for founder_id, members in family_rows.items():
        survivors = [row for row in members if row["death_tick"] is None]
        if not survivors:
            continue

        member_genomes: dict[str, list[Mapping[str, Any]]] = {}
        survivor_genomes: dict[str, list[Mapping[str, Any]]] = {}
        for row in members:
            key = persisted_genome_key(row["genome"])
            member_genomes.setdefault(key, []).append(row)
            if row["death_tick"] is None:
                survivor_genomes.setdefault(key, []).append(row)

        genome_groups = []
        for genome_key, genome_survivors in survivor_genomes.items():
            historical_members = member_genomes[genome_key]
            historical_count = len(historical_members)
            representative = min(
                historical_members,
                key=lambda row: (row["birth_tick"], row["organism_id"]),
            )
            genome_id = genome_display_digest(representative["genome"])
            survivor_items = []
            for row in genome_survivors:
                resolved = ancestry[row["organism_id"]]
                assert resolved is not None
                survivor_items.append(
                    Survivor(
                        organism_id=row["organism_id"],
                        parent_organism_id=row["parent_organism_id"],
                        age=row["lifespan"],
                        generation=resolved[1],
                        child_count=len(
                            children_by_parent.get(row["organism_id"], [])
                        ),
                        final_energy=float(row["final_energy"]),
                        birth_tick=row["birth_tick"],
                        genome_id=genome_id,
                    )
                )
            survivor_items.sort(key=lambda item: (-item.age, item.organism_id))
            ages = [item.age for item in survivor_items]
            child_counts = [item.child_count for item in survivor_items]
            generations = [item.generation for item in survivor_items]
            genome_groups.append(
                SurvivorGenomeGroup(
                    genome_id=genome_id,
                    representative_organism_id=representative["organism_id"],
                    survivor_count=len(survivor_items),
                    historical_organism_count=historical_count,
                    survivor_percentage=(
                        len(survivor_items) / historical_count * 100.0
                    ),
                    average_age=sum(ages) / len(ages),
                    oldest_age=max(ages),
                    average_children=sum(child_counts) / len(child_counts),
                    maximum_children=max(child_counts),
                    first_generation=min(generations),
                    latest_generation=max(generations),
                    survivors=tuple(survivor_items),
                )
            )
        genome_groups.sort(
            key=lambda group: (-group.survivor_count, group.genome_id)
        )

        survivor_ids = {row["organism_id"] for row in survivors}
        descendant_survivors = len(survivor_ids - {founder_id})
        total_descendants = len(members) - 1
        survivor_ages = [row["lifespan"] for row in survivors]
        survivor_children = [
            len(children_by_parent.get(row["organism_id"], []))
            for row in survivors
        ]
        survivor_generations = [
            ancestry[row["organism_id"]][1]  # type: ignore[index]
            for row in survivors
        ]
        founder = organisms[founder_id]
        founder_groups.append(
            SurvivorFounderGroup(
                founder_organism_id=founder_id,
                survivor_count=len(survivors),
                surviving_descendant_count=descendant_survivors,
                total_descendants=total_descendants,
                descendant_survivor_percentage=(
                    descendant_survivors / total_descendants * 100.0
                    if total_descendants
                    else 0.0
                ),
                distinct_survivor_genomes=len(genome_groups),
                average_age=sum(survivor_ages) / len(survivor_ages),
                oldest_age=max(survivor_ages),
                average_children=(
                    sum(survivor_children) / len(survivor_children)
                ),
                maximum_children=max(survivor_children),
                latest_generation=max(survivor_generations),
                founder_lifespan=founder["lifespan"],
                founder_alive_at_end=founder["death_tick"] is None,
                genomes=tuple(genome_groups),
            )
        )

    founder_groups.sort(
        key=lambda founder: (
            -founder.surviving_descendant_count,
            -founder.survivor_count,
            founder.founder_organism_id,
        )
    )
    return SurvivorExplorer(founders=tuple(founder_groups))
