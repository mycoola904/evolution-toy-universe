from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Literal

from domain.action import Action
from domain.simulation import Simulation
from experiments.report import ExperimentReport, build_experiment_report


TerminationReason = Literal["extinction", "tick_limit"]


@dataclass(frozen=True)
class SimulationRunResult:
    started_at: datetime
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

    def __post_init__(self) -> None:
        if (
            self.started_at.tzinfo is None
            or self.started_at.utcoffset() is None
        ):
            raise ValueError("started_at must be timezone-aware")
        object.__setattr__(
            self,
            "started_at",
            self.started_at.astimezone(timezone.utc),
        )


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
    wait_count: int | None = None
    eat_attempt_count: int | None = None
    successful_eat_count: int | None = None
    unsuccessful_eat_count: int | None = None
    move_forward_count: int | None = None
    turn_left_count: int | None = None
    turn_right_count: int | None = None
    final_action: str | None = None

    def __post_init__(self) -> None:
        counts = (
            self.wait_count,
            self.eat_attempt_count,
            self.successful_eat_count,
            self.unsuccessful_eat_count,
            self.move_forward_count,
            self.turn_left_count,
            self.turn_right_count,
        )
        if all(count is None for count in counts):
            if self.final_action is not None:
                raise ValueError("legacy behavior cannot have a final action")
            return
        if any(count is None for count in counts):
            raise ValueError("organism behavior counts must be complete or unavailable")
        if any(count < 0 for count in counts if count is not None):
            raise ValueError("organism behavior counts must be nonnegative")
        if (
            self.successful_eat_count + self.unsuccessful_eat_count
            != self.eat_attempt_count
        ):
            raise ValueError("successful and unsuccessful EATs must equal attempts")
        if self.move_forward_count != self.distance_moved:
            raise ValueError("MOVE_FORWARD count must match distance_moved")
        total_actions = (
            self.wait_count
            + self.eat_attempt_count
            + self.move_forward_count
            + self.turn_left_count
            + self.turn_right_count
        )
        if total_actions != self.lifespan:
            raise ValueError("total actions must match lifespan")
        valid_actions = {action.name for action in Action}
        if self.final_action is not None and self.final_action not in valid_actions:
            raise ValueError("final_action must be a known action")
        if (self.final_action is None) != (total_actions == 0):
            raise ValueError("final_action must exist exactly when actions exist")

    @property
    def received_mutation(self) -> bool | None:
        if self.mutated_weight_count is None:
            return None
        return self.mutated_weight_count > 0


@dataclass(frozen=True)
class ExperimentResult:
    run: SimulationRunResult
    organisms: tuple[OrganismResult, ...]
    report: ExperimentReport | None = None


def build_experiment_result(
    simulation: Simulation,
    started_at: datetime,
    git_commit: str | None,
    git_dirty: bool | None,
) -> ExperimentResult:
    if started_at.tzinfo is None:
        raise ValueError("started_at must be timezone-aware")

    normalized_started_at = started_at.astimezone(timezone.utc)
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
            wait_count=metrics.action_counts[Action.WAIT],
            eat_attempt_count=metrics.action_counts[Action.EAT],
            successful_eat_count=metrics.successful_eats,
            unsuccessful_eat_count=metrics.unsuccessful_eats,
            move_forward_count=metrics.action_counts[Action.MOVE_FORWARD],
            turn_left_count=metrics.action_counts[Action.TURN_LEFT],
            turn_right_count=metrics.action_counts[Action.TURN_RIGHT],
            final_action=(
                metrics.final_action.name if metrics.final_action is not None else None
            ),
        )
        for metrics in sorted(
            simulation.metrics.organism_metrics.values(),
            key=lambda metrics: metrics.organism_id,
        )
    )

    return ExperimentResult(
        run=run,
        organisms=organism_results,
        report=build_experiment_report(simulation),
    )
