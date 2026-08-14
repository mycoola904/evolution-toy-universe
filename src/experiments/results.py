from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Literal

from domain.action import Action
from domain.simulation import Simulation


TerminationReason = Literal["extinction", "tick_limit"]


@dataclass(frozen=True)
class SimulationRunResult:
    started_at: str
    seed: int
    world_width: int
    world_height: int
    ticks_completed: int
    initial_organism_count: int
    ending_organism_count: int
    termination_reason: TerminationReason
    config: dict
    git_commit: str | None
    git_dirty: bool | None


@dataclass(frozen=True)
class OrganismResult:
    organism_id: int
    parent_organism_id: int | None
    birth_tick: int
    mutated_weight_count: int | None
    death_tick: int | None
    lifespan: int
    initial_energy: float
    final_energy: float
    peak_energy: float
    energy_consumed: float
    distance_moved: int
    genome: dict

    @property
    def received_mutation(self) -> bool | None:
        if self.mutated_weight_count is None:
            return None
        return self.mutated_weight_count > 0


@dataclass(frozen=True)
class ExperimentResult:
    run: SimulationRunResult
    organisms: tuple[OrganismResult, ...]


def build_experiment_result(
    simulation: Simulation,
    started_at: datetime,
    git_commit: str | None,
    git_dirty: bool | None,
) -> ExperimentResult:
    if started_at.tzinfo is None:
        raise ValueError("started_at must be timezone-aware")

    normalized_started_at = started_at.astimezone(timezone.utc).isoformat()
    termination_reason: TerminationReason = (
        "extinction" if not simulation.organisms else "tick_limit"
    )

    run = SimulationRunResult(
        started_at=normalized_started_at,
        seed=simulation.config.seed,
        world_width=simulation.config.world_width,
        world_height=simulation.config.world_height,
        ticks_completed=simulation.tick,
        initial_organism_count=simulation.config.initial_organisms,
        ending_organism_count=len(simulation.organisms),
        termination_reason=termination_reason,
        config=asdict(simulation.config),
        git_commit=git_commit,
        git_dirty=git_dirty,
    )

    organism_results = tuple(
        OrganismResult(
            organism_id=metrics.organism_id,
            parent_organism_id=metrics.parent_id,
            birth_tick=metrics.birth_tick,
            mutated_weight_count=metrics.mutated_weight_count,
            death_tick=metrics.death_tick,
            lifespan=(
                (
                    simulation.tick
                    if metrics.death_tick is None
                    else metrics.death_tick
                )
                - metrics.birth_tick
            ),
            initial_energy=metrics.initial_energy,
            final_energy=metrics.final_energy,
            peak_energy=metrics.peak_energy,
            energy_consumed=metrics.energy_eaten,
            distance_moved=metrics.action_counts[
                Action.MOVE_FORWARD
            ],
            genome=metrics.genome.to_dict(),
        )
        for metrics in sorted(
            simulation.metrics.organism_metrics.values(),
            key=lambda metrics: metrics.organism_id,
        )
    )

    return ExperimentResult(run=run, organisms=organism_results)
