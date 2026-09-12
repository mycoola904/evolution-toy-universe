from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from experiments.genomes import genome_display_digest, persisted_genome_key
from experiments.organism_inspection import (
    GenomeComparison,
    GenomeWeightDifference,
    compare_persisted_genomes,
)


@dataclass(frozen=True)
class MutationBranchContext:
    direct_children: int
    total_known_descendants: int
    surviving_descendants: int
    deepest_descendant_generation: int | None
    descendants_include_selected_genome: bool


@dataclass(frozen=True)
class LineageMutationNode:
    organism_id: int
    parent_organism_id: int | None
    generation: int | None
    birth_tick: int
    genome_digest: str
    comparison: GenomeComparison | None
    changes: tuple[GenomeWeightDifference, ...]
    branch: MutationBranchContext

    @property
    def has_mutation(self) -> bool:
        return bool(self.changes)


@dataclass(frozen=True)
class MutationOnlyStep:
    node: LineageMutationNode
    skipped_unchanged_generations: int


@dataclass(frozen=True)
class CumulativeGenomeDifference:
    path: str
    founder_value: float | None
    selected_value: float | None
    net_delta: float | None
    direction: str
    mutation_count: int


@dataclass(frozen=True)
class LineageMutationExplorer:
    founder_organism_id: int
    selected_genome_digest: str
    representative_organism_id: int
    representative_generation: int | None
    representative_birth_tick: int
    ancestry_complete: bool
    ancestry_warning: str | None
    path: tuple[LineageMutationNode, ...]
    mutation_only_steps: tuple[MutationOnlyStep, ...]
    cumulative_differences: tuple[CumulativeGenomeDifference, ...]
    total_mutation_events: int
    total_weight_changes: int
    unique_weights_changed: int

    @property
    def generations_from_founder(self) -> int | None:
        return self.representative_generation


def _comparison_changes(
    comparison: GenomeComparison | None,
) -> tuple[GenomeWeightDifference, ...]:
    if comparison is None:
        return ()
    threshold = (
        (comparison.reproduction_threshold_difference,)
        if comparison.reproduction_threshold_difference is not None
        else ()
    )
    return (*threshold, *comparison.changed_weights)


def build_lineage_mutation_explorer(
    rows: Iterable[Mapping[str, Any]],
    *,
    founder_organism_id: int,
    selected_genome_organism_id: int,
) -> LineageMutationExplorer | None:
    """Trace the earliest carrier of an exact persisted genome to its founder.

    The organism ID selects the persisted genome value, not the display digest.
    Among matching organisms in the founder family, the representative is the
    earliest birth tick, then the lowest organism ID.
    """
    organisms = {row["organism_id"]: row for row in rows}
    selected = organisms.get(selected_genome_organism_id)
    if selected is None:
        return None

    founder_cache: dict[int, int | None] = {}

    def known_founder(organism_id: int) -> int | None:
        path: list[int] = []
        seen: set[int] = set()
        current_id = organism_id
        resolved = None
        while current_id not in seen:
            seen.add(current_id)
            if current_id in founder_cache:
                resolved = founder_cache[current_id]
                break
            current = organisms.get(current_id)
            if current is None:
                break
            path.append(current_id)
            parent_id = current["parent_organism_id"]
            if parent_id is None:
                resolved = current_id if current["birth_tick"] == 0 else None
                break
            current_id = parent_id
        for path_id in path:
            founder_cache[path_id] = resolved
        return resolved

    selected_key = persisted_genome_key(selected["genome"])
    selected_founder = known_founder(selected_genome_organism_id)
    if (
        selected_founder is not None
        and selected_founder != founder_organism_id
    ):
        return None

    candidates = [
        row
        for row in organisms.values()
        if persisted_genome_key(row["genome"]) == selected_key
        and known_founder(row["organism_id"]) == founder_organism_id
    ]
    if not candidates:
        candidates = [selected]
    representative = min(
        candidates,
        key=lambda row: (row["birth_tick"], row["organism_id"]),
    )

    reverse_path: list[Mapping[str, Any]] = []
    visited: set[int] = set()
    current = representative
    ancestry_complete = False
    ancestry_warning = None
    while True:
        current_id = current["organism_id"]
        if current_id in visited:
            ancestry_warning = "An ancestry cycle prevented reconstruction."
            break
        visited.add(current_id)
        reverse_path.append(current)
        parent_id = current["parent_organism_id"]
        if parent_id is None:
            if current_id == founder_organism_id and current["birth_tick"] == 0:
                ancestry_complete = True
            else:
                ancestry_warning = (
                    f"Known ancestry ends at organism {current_id}; "
                    f"founder {founder_organism_id} was not reached."
                )
            break
        parent = organisms.get(parent_id)
        if parent is None:
            ancestry_warning = (
                f"Parent organism {parent_id} is unavailable; the earlier "
                "ancestry path cannot be reconstructed."
            )
            break
        current = parent

    path_rows = list(reversed(reverse_path))
    children_by_parent: dict[int, list[int]] = {}
    for row in organisms.values():
        parent_id = row["parent_organism_id"]
        if parent_id is not None:
            children_by_parent.setdefault(parent_id, []).append(
                row["organism_id"]
            )

    # Aggregate every known subtree once, avoiding a fresh descendant scan for
    # every generation in a long selected path.
    subtree_size = {organism_id: 1 for organism_id in organisms}
    subtree_survivors = {
        organism_id: int(row["death_tick"] is None)
        for organism_id, row in organisms.items()
    }
    subtree_maximum_depth = {organism_id: 0 for organism_id in organisms}
    subtree_selected_genomes = {
        organism_id: int(persisted_genome_key(row["genome"]) == selected_key)
        for organism_id, row in organisms.items()
    }
    remaining_children = {
        organism_id: sum(
            child_id in organisms
            for child_id in children_by_parent.get(organism_id, [])
        )
        for organism_id in organisms
    }
    ready = [
        organism_id
        for organism_id, count in remaining_children.items()
        if count == 0
    ]
    while ready:
        child_id = ready.pop()
        parent_id = organisms[child_id]["parent_organism_id"]
        if parent_id not in organisms:
            continue
        subtree_size[parent_id] += subtree_size[child_id]
        subtree_survivors[parent_id] += subtree_survivors[child_id]
        subtree_maximum_depth[parent_id] = max(
            subtree_maximum_depth[parent_id],
            subtree_maximum_depth[child_id] + 1,
        )
        subtree_selected_genomes[parent_id] += subtree_selected_genomes[child_id]
        remaining_children[parent_id] -= 1
        if remaining_children[parent_id] == 0:
            ready.append(parent_id)

    def branch_context(
        organism_id: int,
        generation: int | None,
    ) -> MutationBranchContext:
        maximum_depth = subtree_maximum_depth[organism_id]
        organism_is_selected_genome = int(
            persisted_genome_key(organisms[organism_id]["genome"])
            == selected_key
        )
        return MutationBranchContext(
            direct_children=sum(
                child_id in organisms
                for child_id in children_by_parent.get(organism_id, [])
            ),
            total_known_descendants=subtree_size[organism_id] - 1,
            surviving_descendants=(
                subtree_survivors[organism_id]
                - int(organisms[organism_id]["death_tick"] is None)
            ),
            deepest_descendant_generation=(
                generation + maximum_depth
                if generation is not None and maximum_depth > 0
                else None
            ),
            descendants_include_selected_genome=(
                subtree_selected_genomes[organism_id]
                - organism_is_selected_genome
                > 0
            ),
        )

    nodes = []
    for index, row in enumerate(path_rows):
        generation = index if ancestry_complete else None
        comparison = None
        if index:
            comparison = compare_persisted_genomes(
                path_rows[index - 1]["genome"],
                row["genome"],
                recorded_mutated_weight_count=row.get(
                    "mutated_weight_count"
                ),
            )
        nodes.append(
            LineageMutationNode(
                organism_id=row["organism_id"],
                parent_organism_id=row["parent_organism_id"],
                generation=generation,
                birth_tick=row["birth_tick"],
                genome_digest=genome_display_digest(row["genome"]),
                comparison=comparison,
                changes=_comparison_changes(comparison),
                branch=branch_context(row["organism_id"], generation),
            )
        )

    included_indexes = [0]
    included_indexes.extend(
        index for index, node in enumerate(nodes[1:], 1) if node.has_mutation
    )
    if len(nodes) > 1 and included_indexes[-1] != len(nodes) - 1:
        included_indexes.append(len(nodes) - 1)
    mutation_steps = []
    previous_index = None
    for index in included_indexes:
        mutation_steps.append(
            MutationOnlyStep(
                node=nodes[index],
                skipped_unchanged_generations=(
                    0
                    if previous_index is None
                    else max(0, index - previous_index - 1)
                ),
            )
        )
        previous_index = index

    mutation_counts: dict[str, int] = {}
    for node in nodes:
        for change in node.changes:
            mutation_counts[change.path] = mutation_counts.get(change.path, 0) + 1

    cumulative_differences = []
    if ancestry_complete and nodes:
        cumulative = compare_persisted_genomes(
            path_rows[0]["genome"],
            representative["genome"],
            recorded_mutated_weight_count=None,
        )
        for change in _comparison_changes(cumulative):
            cumulative_differences.append(
                CumulativeGenomeDifference(
                    path=change.path,
                    founder_value=change.parent_value,
                    selected_value=change.child_value,
                    net_delta=change.delta,
                    direction=change.direction,
                    mutation_count=mutation_counts.get(change.path, 0),
                )
            )

    comparisons = [
        node.comparison for node in nodes if node.comparison is not None
    ]
    return LineageMutationExplorer(
        founder_organism_id=founder_organism_id,
        selected_genome_digest=genome_display_digest(representative["genome"]),
        representative_organism_id=representative["organism_id"],
        representative_generation=(len(nodes) - 1 if ancestry_complete else None),
        representative_birth_tick=representative["birth_tick"],
        ancestry_complete=ancestry_complete,
        ancestry_warning=ancestry_warning,
        path=tuple(nodes),
        mutation_only_steps=tuple(mutation_steps),
        cumulative_differences=tuple(cumulative_differences),
        total_mutation_events=sum(node.has_mutation for node in nodes),
        total_weight_changes=sum(
            comparison.changed_weight_count for comparison in comparisons
        ),
        unique_weights_changed=len(
            {
                change.path
                for comparison in comparisons
                for change in comparison.changed_weights
            }
        ),
    )
