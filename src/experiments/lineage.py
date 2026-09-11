from dataclasses import dataclass
from typing import Any, Iterable, Mapping


@dataclass(frozen=True)
class LineageOrganism:
    organism_id: int
    parent_organism_id: int | None
    birth_tick: int
    death_tick: int | None
    lifespan: int
    mutated_weight_count: int | None
    energy_consumed: float
    distance_moved: int


@dataclass(frozen=True)
class FamilyTreeNode:
    organism_id: int
    parent_organism_id: int | None
    birth_tick: int
    death_tick: int | None
    lifespan: int
    generation: int
    received_mutation: bool | None
    mutated_weight_count: int | None
    children: tuple["FamilyTreeNode", ...]

    @property
    def child_count(self) -> int:
        return len(self.children)


@dataclass(frozen=True)
class FamilySummary:
    founder_organism_id: int
    total_family_members: int
    total_descendants: int
    generations_reached: int
    alive_at_end: int
    dead: int
    reproducing_family_members: int
    total_births_produced: int
    longest_lived_organism_id: int
    longest_lifespan: int
    total_energy_consumed: float
    average_energy_consumed: float
    total_distance_moved: int
    average_distance_moved: float
    organisms_that_received_mutation: int
    total_mutated_weights: int
    extinction_tick: int | None
    lineage_survived: bool


@dataclass(frozen=True)
class LineageAnalysis:
    families: tuple[FamilySummary, ...]
    trees_by_founder: Mapping[int, FamilyTreeNode]


def _organism_from_row(row: Mapping[str, Any]) -> LineageOrganism:
    return LineageOrganism(
        organism_id=row["organism_id"],
        parent_organism_id=row["parent_organism_id"],
        birth_tick=row["birth_tick"],
        death_tick=row["death_tick"],
        lifespan=row["lifespan"],
        mutated_weight_count=row["mutated_weight_count"],
        energy_consumed=float(row["energy_consumed"]),
        distance_moved=row["distance_moved"],
    )


def analyze_lineages(rows: Iterable[Mapping[str, Any]]) -> LineageAnalysis:
    """Reconstruct founder families from one run's normalized organism rows.

    Founders have no parent and are born at tick zero. The founder is generation
    zero, so ``generations_reached`` is the maximum descendant depth. A family
    survives when at least one member has no death tick at experiment end.
    """
    organisms = {
        organism.organism_id: organism
        for organism in (_organism_from_row(row) for row in rows)
    }
    children_by_parent: dict[int, list[int]] = {}
    for organism in organisms.values():
        if organism.parent_organism_id is not None:
            children_by_parent.setdefault(
                organism.parent_organism_id,
                [],
            ).append(organism.organism_id)
    for child_ids in children_by_parent.values():
        child_ids.sort()

    def build_tree(
        organism_id: int,
        generation: int,
        ancestors: frozenset[int],
    ) -> FamilyTreeNode:
        if organism_id in ancestors:
            raise ValueError("lineage contains a parent-child cycle")
        organism = organisms[organism_id]
        next_ancestors = ancestors | {organism_id}
        children = tuple(
            build_tree(child_id, generation + 1, next_ancestors)
            for child_id in children_by_parent.get(organism_id, [])
            if child_id in organisms
        )
        return FamilyTreeNode(
            organism_id=organism.organism_id,
            parent_organism_id=organism.parent_organism_id,
            birth_tick=organism.birth_tick,
            death_tick=organism.death_tick,
            lifespan=organism.lifespan,
            generation=generation,
            received_mutation=(
                None
                if organism.mutated_weight_count is None
                else organism.mutated_weight_count > 0
            ),
            mutated_weight_count=organism.mutated_weight_count,
            children=children,
        )

    def flatten(tree: FamilyTreeNode) -> list[FamilyTreeNode]:
        return [tree, *(item for child in tree.children for item in flatten(child))]

    founders = sorted(
        organism.organism_id
        for organism in organisms.values()
        if organism.parent_organism_id is None and organism.birth_tick == 0
    )
    trees = {founder_id: build_tree(founder_id, 0, frozenset()) for founder_id in founders}
    summaries = []
    for founder_id, tree in trees.items():
        nodes = flatten(tree)
        family_organisms = [organisms[node.organism_id] for node in nodes]
        alive_at_end = sum(item.death_tick is None for item in family_organisms)
        longest = max(
            family_organisms,
            key=lambda item: (item.lifespan, -item.organism_id),
        )
        total_energy = sum(item.energy_consumed for item in family_organisms)
        total_distance = sum(item.distance_moved for item in family_organisms)
        total_members = len(family_organisms)
        summaries.append(
            FamilySummary(
                founder_organism_id=founder_id,
                total_family_members=total_members,
                total_descendants=total_members - 1,
                generations_reached=max(node.generation for node in nodes),
                alive_at_end=alive_at_end,
                dead=total_members - alive_at_end,
                reproducing_family_members=sum(
                    bool(node.children) for node in nodes
                ),
                total_births_produced=sum(len(node.children) for node in nodes),
                longest_lived_organism_id=longest.organism_id,
                longest_lifespan=longest.lifespan,
                total_energy_consumed=total_energy,
                average_energy_consumed=total_energy / total_members,
                total_distance_moved=total_distance,
                average_distance_moved=total_distance / total_members,
                organisms_that_received_mutation=sum(
                    (item.mutated_weight_count or 0) > 0
                    for item in family_organisms
                ),
                total_mutated_weights=sum(
                    item.mutated_weight_count or 0
                    for item in family_organisms
                ),
                extinction_tick=(
                    max(
                        item.death_tick
                        for item in family_organisms
                        if item.death_tick is not None
                    )
                    if alive_at_end == 0
                    else None
                ),
                lineage_survived=alive_at_end > 0,
            )
        )

    summaries.sort(
        key=lambda family: (
            -family.total_descendants,
            -family.generations_reached,
            -family.total_mutated_weights,
            family.founder_organism_id,
        )
    )
    return LineageAnalysis(
        families=tuple(summaries),
        trees_by_founder=trees,
    )
