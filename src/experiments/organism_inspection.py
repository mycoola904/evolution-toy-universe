from dataclasses import dataclass
from typing import Any, Iterable, Mapping


@dataclass(frozen=True)
class GenomeWeightDifference:
    action: str
    weight: str
    parent_value: float | None
    child_value: float | None
    delta: float | None

    @property
    def path(self) -> str:
        return f"{self.action}.{self.weight}"

    @property
    def direction(self) -> str:
        if self.delta is None:
            return "changed"
        if self.delta > 0:
            return "increased"
        if self.delta < 0:
            return "decreased"
        return "unchanged"


@dataclass(frozen=True)
class GenomeComparison:
    changed_weights: tuple[GenomeWeightDifference, ...]
    reproduction_threshold_difference: GenomeWeightDifference | None
    recorded_mutated_weight_count: int | None
    topology_warnings: tuple[str, ...]

    @property
    def identical(self) -> bool:
        return (
            not self.changed_weights
            and self.reproduction_threshold_difference is None
            and not self.topology_warnings
        )

    @property
    def changed_weight_count(self) -> int:
        return len(self.changed_weights)

    @property
    def recorded_count_matches(self) -> bool | None:
        if self.recorded_mutated_weight_count is None:
            return None
        return self.recorded_mutated_weight_count == self.changed_weight_count


@dataclass(frozen=True)
class BehaviorActionStatistic:
    action: str
    count: int
    percentage: float


@dataclass(frozen=True)
class OrganismInspection:
    run_id: int
    organism_id: int
    parent_organism_id: int | None
    founder_organism_id: int | None
    generation: int | None
    birth_tick: int
    death_tick: int | None
    lifespan: int
    mutated_weight_count: int | None
    initial_energy: float
    final_energy: float
    peak_energy: float
    energy_consumed: float
    distance_moved: int
    wait_count: int | None
    eat_attempt_count: int | None
    successful_eat_count: int | None
    unsuccessful_eat_count: int | None
    move_forward_count: int | None
    turn_left_count: int | None
    turn_right_count: int | None
    final_action: str | None
    genome: Mapping[str, Any]
    parent_genome: Mapping[str, Any] | None
    parent_exists: bool
    sibling_organism_ids: tuple[int, ...]
    child_organism_ids: tuple[int, ...]
    genome_comparison: GenomeComparison | None

    @property
    def child_count(self) -> int:
        return len(self.child_organism_ids)

    @property
    def behavior_available(self) -> bool:
        return all(
            count is not None
            for count in (
                self.wait_count,
                self.eat_attempt_count,
                self.successful_eat_count,
                self.unsuccessful_eat_count,
                self.move_forward_count,
                self.turn_left_count,
                self.turn_right_count,
            )
        )

    @property
    def total_actions(self) -> int | None:
        if not self.behavior_available:
            return None
        return sum(
            count
            for count in (
                self.wait_count,
                self.eat_attempt_count,
                self.move_forward_count,
                self.turn_left_count,
                self.turn_right_count,
            )
            if count is not None
        )

    @property
    def eat_success_rate(self) -> float | None:
        if not self.behavior_available or not self.eat_attempt_count:
            return None
        return self.successful_eat_count / self.eat_attempt_count * 100.0

    @property
    def action_distribution(self) -> tuple[BehaviorActionStatistic, ...]:
        if not self.behavior_available:
            return ()
        total = self.total_actions or 0
        action_counts = (
            ("WAIT", self.wait_count),
            ("EAT", self.eat_attempt_count),
            ("MOVE_FORWARD", self.move_forward_count),
            ("TURN_LEFT", self.turn_left_count),
            ("TURN_RIGHT", self.turn_right_count),
        )
        return tuple(
            BehaviorActionStatistic(
                action=action,
                count=count,
                percentage=count / total * 100.0 if total else 0.0,
            )
            for action, count in action_counts
            if count is not None
        )


def _weights(genome: Mapping[str, Any]) -> Mapping[str, Any]:
    weights = genome.get("weights", {})
    return weights if isinstance(weights, Mapping) else {}


def _ordered_union(first: Iterable[str], second: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys((*first, *second)))


def compare_persisted_genomes(
    parent_genome: Mapping[str, Any],
    child_genome: Mapping[str, Any],
    *,
    recorded_mutated_weight_count: int | None,
) -> GenomeComparison:
    """Compare persisted neural weights without assuming a fixed action topology."""
    parent_weights = _weights(parent_genome)
    child_weights = _weights(child_genome)
    changes: list[GenomeWeightDifference] = []
    warnings: list[str] = []

    parent_threshold = parent_genome.get("reproduction_threshold")
    child_threshold = child_genome.get("reproduction_threshold")
    threshold_difference = None
    if parent_threshold != child_threshold:
        parent_number = (
            float(parent_threshold)
            if isinstance(parent_threshold, (int, float))
            else None
        )
        child_number = (
            float(child_threshold)
            if isinstance(child_threshold, (int, float))
            else None
        )
        threshold_difference = GenomeWeightDifference(
            action="GENOME",
            weight="REPRODUCTION_THRESHOLD",
            parent_value=parent_number,
            child_value=child_number,
            delta=(
                child_number - parent_number
                if parent_number is not None and child_number is not None
                else None
            ),
        )

    for action in _ordered_union(child_weights, parent_weights):
        parent_group = parent_weights.get(action)
        child_group = child_weights.get(action)
        if not isinstance(parent_group, Mapping) or not isinstance(child_group, Mapping):
            warnings.append(f"Weight group {action!r} is missing or malformed")
            continue

        for weight in _ordered_union(child_group, parent_group):
            parent_value = parent_group.get(weight)
            child_value = child_group.get(weight)
            if parent_value == child_value:
                continue
            parent_number = (
                float(parent_value) if isinstance(parent_value, (int, float)) else None
            )
            child_number = (
                float(child_value) if isinstance(child_value, (int, float)) else None
            )
            if parent_number is None or child_number is None:
                warnings.append(f"Weight {action}.{weight} is missing or non-numeric")
            changes.append(
                GenomeWeightDifference(
                    action=str(action),
                    weight=str(weight),
                    parent_value=parent_number,
                    child_value=child_number,
                    delta=(
                        child_number - parent_number
                        if parent_number is not None and child_number is not None
                        else None
                    ),
                )
            )

    return GenomeComparison(
        changed_weights=tuple(changes),
        reproduction_threshold_difference=threshold_difference,
        recorded_mutated_weight_count=recorded_mutated_weight_count,
        topology_warnings=tuple(warnings),
    )


def _lineage_context(
    organisms: Mapping[int, Mapping[str, Any]],
    organism_id: int,
) -> tuple[int | None, int | None]:
    current_id = organism_id
    generation = 0
    visited: set[int] = set()
    while True:
        if current_id in visited:
            return None, None
        visited.add(current_id)
        current = organisms.get(current_id)
        if current is None:
            return None, None
        parent_id = current["parent_organism_id"]
        if parent_id is None:
            founder_id = current_id if current["birth_tick"] == 0 else None
            return founder_id, generation if founder_id is not None else None
        current_id = parent_id
        generation += 1


def inspect_organism(
    rows: Iterable[Mapping[str, Any]],
    organism_id: int,
) -> OrganismInspection | None:
    """Build persisted life, relationship, and genome context for one organism."""
    organisms = {row["organism_id"]: row for row in rows}
    organism = organisms.get(organism_id)
    if organism is None:
        return None

    parent_id = organism["parent_organism_id"]
    parent = organisms.get(parent_id) if parent_id is not None else None
    founder_id, generation = _lineage_context(organisms, organism_id)
    siblings = (
        tuple(
            sorted(
                row["organism_id"]
                for row in organisms.values()
                if row["parent_organism_id"] == parent_id
                and row["organism_id"] != organism_id
            )
        )
        if parent_id is not None
        else ()
    )
    children = tuple(
        sorted(
            row["organism_id"]
            for row in organisms.values()
            if row["parent_organism_id"] == organism_id
        )
    )
    genome = organism["genome"]
    comparison = (
        compare_persisted_genomes(
            parent["genome"],
            genome,
            recorded_mutated_weight_count=organism["mutated_weight_count"],
        )
        if parent is not None
        else None
    )

    return OrganismInspection(
        run_id=organism["simulation_run_id"],
        organism_id=organism_id,
        parent_organism_id=parent_id,
        founder_organism_id=founder_id,
        generation=generation,
        birth_tick=organism["birth_tick"],
        death_tick=organism["death_tick"],
        lifespan=organism["lifespan"],
        mutated_weight_count=organism["mutated_weight_count"],
        initial_energy=float(organism["initial_energy"]),
        final_energy=float(organism["final_energy"]),
        peak_energy=float(organism["peak_energy"]),
        energy_consumed=float(organism["energy_consumed"]),
        distance_moved=organism["distance_moved"],
        wait_count=organism.get("wait_count"),
        eat_attempt_count=organism.get("eat_attempt_count"),
        successful_eat_count=organism.get("successful_eat_count"),
        unsuccessful_eat_count=organism.get("unsuccessful_eat_count"),
        move_forward_count=organism.get("move_forward_count"),
        turn_left_count=organism.get("turn_left_count"),
        turn_right_count=organism.get("turn_right_count"),
        final_action=organism.get("final_action"),
        genome=genome,
        parent_genome=parent["genome"] if parent is not None else None,
        parent_exists=parent is not None,
        sibling_organism_ids=siblings,
        child_organism_ids=children,
        genome_comparison=comparison,
    )
