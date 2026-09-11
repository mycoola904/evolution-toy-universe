from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any

from domain.action import Action
from domain.simulation_metrics import OrganismMetrics

if TYPE_CHECKING:
    from domain.simulation import Simulation


@dataclass(frozen=True)
class ExperimentSummaryReport:
    status: str
    seed: int
    world_width: int
    world_height: int
    final_tick: int
    initial_population: int
    remaining_population: int


@dataclass(frozen=True)
class EnvironmentalEnergyReport:
    initial_world_energy: float
    remaining_world_energy: float
    regeneration_energy_attempted: float
    regeneration_energy_added: float
    regeneration_energy_wasted_at_cap: float
    world_energy_consumed: float
    percent_consumed: float
    percent_left_stranded: float
    energy_eaten_on_tick_one: float
    energy_eaten_after_tick_one: float
    percent_consumed_after_tick_one: float
    first_successful_eat_tick: int | None
    last_successful_eat_tick: int | None


@dataclass(frozen=True)
class ActionTotalReport:
    action: str
    count: int
    percent: float


@dataclass(frozen=True)
class EatingReport:
    total_eat_attempts: int
    successful_eat_actions: int
    unsuccessful_eat_actions: int
    eat_success_rate: float
    organisms_that_successfully_ate: int
    total_energy_eaten: float


@dataclass(frozen=True)
class MovementReport:
    total_move_forward_actions: int
    organisms_that_moved: int
    most_moves: int
    most_mobile_organism_ids: tuple[int, ...]


@dataclass(frozen=True)
class ReproductionReport:
    total_births: int
    peak_population: int
    organisms_that_reproduced: int
    first_birth_tick: int | None
    last_birth_tick: int | None
    most_offspring: int
    most_prolific_parent_ids: tuple[int, ...]


@dataclass(frozen=True)
class SurvivalReport:
    last_death_tick: int | None
    longest_longevity: int
    longest_lived_organism_ids: tuple[int, ...]
    number_tied: int


@dataclass(frozen=True)
class NotableOrganismReport:
    organism_id: int
    birth_tick: int
    death_tick: int | None
    longevity: int
    successful_eats: int
    energy_eaten: float
    moves: int
    peak_energy: float
    final_action: str | None


@dataclass(frozen=True)
class RepresentativeGenomeReport:
    representative_organism_id: int
    longest_longevity_ids: tuple[int, ...]
    reproduction_threshold: float
    weights: dict[str, dict[str, float]]


@dataclass(frozen=True)
class ExperimentReport:
    schema_version: int
    summary: ExperimentSummaryReport
    environmental_energy: EnvironmentalEnergyReport
    action_totals: tuple[ActionTotalReport, ...]
    eating: EatingReport
    movement: MovementReport
    reproduction: ReproductionReport
    survival: SurvivalReport
    notable_organisms: dict[str, NotableOrganismReport | None]
    representative_genome: RepresentativeGenomeReport | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _longevity(simulation: "Simulation", metrics: OrganismMetrics) -> int:
    return simulation._longevity(metrics)


def _representative(
    simulation: "Simulation",
    candidates: list[OrganismMetrics],
) -> OrganismMetrics | None:
    return simulation._representative_from_metrics(candidates)


def _best_by_value(
    simulation: "Simulation",
    candidates: list[OrganismMetrics],
    value_fn,
) -> OrganismMetrics | None:
    if not candidates:
        return None
    best_value = max(value_fn(metrics) for metrics in candidates)
    return _representative(
        simulation,
        [metrics for metrics in candidates if value_fn(metrics) == best_value],
    )


def _representative_last_survivor(
    simulation: "Simulation",
    organism_metrics: list[OrganismMetrics],
) -> OrganismMetrics | None:
    if not organism_metrics:
        return None
    if simulation.organisms:
        surviving_ids = {
            organism.organism_id for organism in simulation.organisms
        }
        candidates = [
            metrics
            for metrics in organism_metrics
            if metrics.organism_id in surviving_ids
        ]
    else:
        latest_death_tick = max(
            (
                metrics.death_tick
                for metrics in organism_metrics
                if metrics.death_tick is not None
            ),
            default=None,
        )
        candidates = [
            metrics
            for metrics in organism_metrics
            if metrics.death_tick == latest_death_tick
        ]
    return _representative(simulation, candidates)


def _notable(
    simulation: "Simulation",
    metrics: OrganismMetrics | None,
) -> NotableOrganismReport | None:
    if metrics is None:
        return None
    return NotableOrganismReport(
        organism_id=metrics.organism_id,
        birth_tick=metrics.birth_tick,
        death_tick=metrics.death_tick,
        longevity=_longevity(simulation, metrics),
        successful_eats=metrics.successful_eats,
        energy_eaten=metrics.energy_eaten,
        moves=metrics.action_counts[Action.MOVE_FORWARD],
        peak_energy=metrics.peak_energy,
        final_action=(
            None if metrics.final_action is None else metrics.final_action.name
        ),
    )


def build_experiment_report(simulation: "Simulation") -> ExperimentReport:
    """Build an observational snapshot without advancing or mutating a run."""
    simulation._run_consistency_checks()
    organism_metrics = list(simulation.metrics.organism_metrics.values())
    remaining_world_energy = simulation.total_world_energy()
    total_world_energy_available = (
        simulation.initial_world_energy
        + simulation.metrics.regeneration_energy_added
    )
    consumed_world_energy = simulation.metrics.total_energy_eaten
    percent_consumed = (
        consumed_world_energy / total_world_energy_available * 100.0
        if total_world_energy_available > 0
        else 0.0
    )
    percent_remaining = (
        remaining_world_energy / total_world_energy_available * 100.0
        if total_world_energy_available > 0
        else 0.0
    )
    percent_after_tick_one = (
        simulation.metrics.after_tick_one_energy_eaten
        / consumed_world_energy
        * 100.0
        if consumed_world_energy > 0
        else 0.0
    )

    total_actions = sum(simulation.metrics.action_counts.values())
    action_totals = tuple(
        ActionTotalReport(
            action=action.name,
            count=simulation.metrics.action_counts[action],
            percent=(
                simulation.metrics.action_counts[action] / total_actions * 100.0
                if total_actions > 0
                else 0.0
            ),
        )
        for action in Action
    )
    total_eat_attempts = simulation.metrics.action_counts[Action.EAT]
    most_moves = max(
        (
            metrics.action_counts[Action.MOVE_FORWARD]
            for metrics in organism_metrics
        ),
        default=0,
    )
    most_move_ids = tuple(
        sorted(
            metrics.organism_id
            for metrics in organism_metrics
            if most_moves > 0
            and metrics.action_counts[Action.MOVE_FORWARD] == most_moves
        )
    )
    most_offspring = max(
        (metrics.offspring_count for metrics in organism_metrics),
        default=0,
    )
    most_offspring_ids = tuple(
        sorted(
            metrics.organism_id
            for metrics in organism_metrics
            if most_offspring > 0 and metrics.offspring_count == most_offspring
        )
    )
    longest_longevity = max(
        (_longevity(simulation, metrics) for metrics in organism_metrics),
        default=0,
    )
    longest_metrics = [
        metrics
        for metrics in organism_metrics
        if _longevity(simulation, metrics) == longest_longevity
    ]
    longest_ids = tuple(
        sorted(metrics.organism_id for metrics in longest_metrics)
    )
    last_survivor = _representative_last_survivor(
        simulation,
        organism_metrics,
    )

    notable_metrics = {
        "longest_lived": _representative(simulation, longest_metrics),
        "largest_energy_consumer": _best_by_value(
            simulation,
            organism_metrics,
            lambda metrics: metrics.energy_eaten,
        ),
        "most_mobile": _best_by_value(
            simulation,
            organism_metrics,
            lambda metrics: metrics.action_counts[Action.MOVE_FORWARD],
        ),
        "highest_peak_energy": _best_by_value(
            simulation,
            organism_metrics,
            lambda metrics: metrics.peak_energy,
        ),
    }

    representative_genome = None
    if last_survivor is not None:
        genome = last_survivor.genome.to_dict()
        representative_genome = RepresentativeGenomeReport(
            representative_organism_id=last_survivor.organism_id,
            longest_longevity_ids=longest_ids,
            reproduction_threshold=genome["reproduction_threshold"],
            weights=genome["weights"],
        )

    return ExperimentReport(
        schema_version=1,
        summary=ExperimentSummaryReport(
            status=(
                "TICK LIMIT REACHED"
                if simulation.organisms
                else "POPULATION EXTINCT"
            ),
            seed=simulation.config.seed,
            world_width=simulation.config.world_width,
            world_height=simulation.config.world_height,
            final_tick=simulation.tick,
            initial_population=simulation.config.initial_organisms,
            remaining_population=len(simulation.organisms),
        ),
        environmental_energy=EnvironmentalEnergyReport(
            initial_world_energy=simulation.initial_world_energy,
            remaining_world_energy=remaining_world_energy,
            regeneration_energy_attempted=(
                simulation.metrics.regeneration_energy_attempted
            ),
            regeneration_energy_added=simulation.metrics.regeneration_energy_added,
            regeneration_energy_wasted_at_cap=(
                simulation.metrics.regeneration_energy_wasted
            ),
            world_energy_consumed=consumed_world_energy,
            percent_consumed=percent_consumed,
            percent_left_stranded=percent_remaining,
            energy_eaten_on_tick_one=simulation.metrics.tick_one_energy_eaten,
            energy_eaten_after_tick_one=(
                simulation.metrics.after_tick_one_energy_eaten
            ),
            percent_consumed_after_tick_one=percent_after_tick_one,
            first_successful_eat_tick=(
                simulation.metrics.first_successful_eat_tick
            ),
            last_successful_eat_tick=simulation.metrics.last_successful_eat_tick,
        ),
        action_totals=action_totals,
        eating=EatingReport(
            total_eat_attempts=total_eat_attempts,
            successful_eat_actions=simulation.metrics.successful_eats,
            unsuccessful_eat_actions=simulation.metrics.unsuccessful_eats,
            eat_success_rate=(
                simulation.metrics.successful_eats / total_eat_attempts * 100.0
                if total_eat_attempts > 0
                else 0.0
            ),
            organisms_that_successfully_ate=sum(
                metrics.successful_eats > 0 for metrics in organism_metrics
            ),
            total_energy_eaten=simulation.metrics.total_energy_eaten,
        ),
        movement=MovementReport(
            total_move_forward_actions=(
                simulation.metrics.action_counts[Action.MOVE_FORWARD]
            ),
            organisms_that_moved=sum(
                metrics.action_counts[Action.MOVE_FORWARD] > 0
                for metrics in organism_metrics
            ),
            most_moves=most_moves,
            most_mobile_organism_ids=most_move_ids,
        ),
        reproduction=ReproductionReport(
            total_births=simulation.metrics.total_births,
            peak_population=simulation.metrics.peak_population,
            organisms_that_reproduced=sum(
                metrics.offspring_count > 0 for metrics in organism_metrics
            ),
            first_birth_tick=simulation.metrics.first_birth_tick,
            last_birth_tick=simulation.metrics.last_birth_tick,
            most_offspring=most_offspring,
            most_prolific_parent_ids=most_offspring_ids,
        ),
        survival=SurvivalReport(
            last_death_tick=max(
                (
                    metrics.death_tick
                    for metrics in organism_metrics
                    if metrics.death_tick is not None
                ),
                default=None,
            ),
            longest_longevity=longest_longevity,
            longest_lived_organism_ids=longest_ids,
            number_tied=len(longest_ids),
        ),
        notable_organisms={
            name: _notable(simulation, metrics)
            for name, metrics in notable_metrics.items()
        },
        representative_genome=representative_genome,
    )


def _format_count(value: int) -> str:
    return f"{value:,}"


def _format_optional(value: int | None) -> str:
    return "NONE" if value is None else str(value)


def _format_ids(values: tuple[int, ...]) -> str:
    return "NONE" if not values else ", ".join(map(str, values))


def _kv(label: str, value: str, indent: int = 0) -> str:
    return f"{' ' * indent}{label:<44} {value}"


def format_experiment_report(report: ExperimentReport) -> str:
    """Format the shared report using the established CLI presentation."""
    summary = report.summary
    energy = report.environmental_energy
    lines = [
        "",
        "=" * 60,
        "EXPERIMENT REPORT",
        "=" * 60,
        "-" * 60,
        "EXPERIMENT SUMMARY",
        _kv("Status", summary.status),
        _kv("Seed", str(summary.seed)),
        _kv("World dimensions", f"{summary.world_width}x{summary.world_height}"),
        _kv("Final tick", _format_count(summary.final_tick)),
        _kv("Initial population", _format_count(summary.initial_population)),
        _kv("Remaining population", _format_count(summary.remaining_population)),
        "-" * 60,
        "ENVIRONMENTAL ENERGY",
        _kv("Initial world energy", f"{energy.initial_world_energy:.2f}"),
        _kv("Remaining world energy", f"{energy.remaining_world_energy:.2f}"),
        _kv(
            "Regeneration energy attempted",
            f"{energy.regeneration_energy_attempted:.2f}",
        ),
        _kv("Regeneration energy added", f"{energy.regeneration_energy_added:.2f}"),
        _kv(
            "Regeneration energy wasted at cap",
            f"{energy.regeneration_energy_wasted_at_cap:.2f}",
        ),
        _kv("World energy consumed", f"{energy.world_energy_consumed:.2f}"),
        _kv("Percent consumed", f"{energy.percent_consumed:.2f}%"),
        _kv("Percent left stranded", f"{energy.percent_left_stranded:.2f}%"),
        _kv("Energy eaten on tick 1", f"{energy.energy_eaten_on_tick_one:.2f}"),
        _kv(
            "Energy eaten after tick 1",
            f"{energy.energy_eaten_after_tick_one:.2f}",
        ),
        _kv(
            "Percent of consumed energy eaten after tick 1",
            f"{energy.percent_consumed_after_tick_one:.2f}%",
        ),
        _kv("First successful EAT tick", _format_optional(energy.first_successful_eat_tick)),
        _kv("Last successful EAT tick", _format_optional(energy.last_successful_eat_tick)),
        "-" * 60,
        "ACTION TOTALS",
        f"{'Action':<13} {'Count':>10} {'Percent':>10}",
    ]
    lines.extend(
        f"{item.action:<13} {item.count:>10,} {item.percent:>9.2f}%"
        for item in report.action_totals
    )
    eating = report.eating
    lines.extend(
        [
            "-" * 60,
            "EATING RESULTS",
            _kv("Total EAT attempts", _format_count(eating.total_eat_attempts)),
            _kv("Successful EAT actions", _format_count(eating.successful_eat_actions)),
            _kv("Unsuccessful EAT actions", _format_count(eating.unsuccessful_eat_actions)),
            _kv("EAT success rate", f"{eating.eat_success_rate:.2f}%"),
            _kv(
                "Organisms that successfully ate",
                _format_count(eating.organisms_that_successfully_ate),
            ),
            _kv("Total energy eaten", f"{eating.total_energy_eaten:.2f}"),
            "-" * 60,
            "MOVEMENT RESULTS",
            _kv(
                "Total MOVE_FORWARD actions",
                _format_count(report.movement.total_move_forward_actions),
            ),
            _kv(
                "Organisms that moved at least once",
                _format_count(report.movement.organisms_that_moved),
            ),
            _kv("Most moves by one organism", _format_count(report.movement.most_moves)),
            _kv(
                "Organism ID with the most moves",
                (
                    str(report.movement.most_mobile_organism_ids[0])
                    if report.movement.most_mobile_organism_ids
                    else "NONE"
                ),
            ),
        ]
    )
    if report.movement.most_mobile_organism_ids:
        lines.append(
            _kv(
                "Organism IDs tied for most moves",
                _format_ids(report.movement.most_mobile_organism_ids),
            )
        )
    reproduction = report.reproduction
    survival = report.survival
    lines.extend(
        [
            "-" * 60,
            "REPRODUCTION RESULTS",
            _kv("Total births", _format_count(reproduction.total_births)),
            _kv("Peak population", _format_count(reproduction.peak_population)),
            _kv(
                "Organisms that reproduced",
                _format_count(reproduction.organisms_that_reproduced),
            ),
            _kv("First birth tick", _format_optional(reproduction.first_birth_tick)),
            _kv("Last birth tick", _format_optional(reproduction.last_birth_tick)),
            _kv("Most offspring by one organism", _format_count(reproduction.most_offspring)),
            _kv(
                "Parent ID(s) with most offspring",
                _format_ids(reproduction.most_prolific_parent_ids),
            ),
            "-" * 60,
            "SURVIVAL RESULTS",
            _kv("Last death tick", _format_optional(survival.last_death_tick)),
            _kv("Longest longevity (ticks)", _format_count(survival.longest_longevity)),
            _kv(
                "Longest-longevity organism IDs",
                _format_ids(survival.longest_lived_organism_ids),
            ),
            _kv("Number tied for longest survival", _format_count(survival.number_tied)),
            "-" * 60,
            "NOTABLE ORGANISMS",
        ]
    )
    labels = {
        "longest_lived": "Longest-lived organism",
        "largest_energy_consumer": "Largest energy consumer",
        "most_mobile": "Most mobile organism",
        "highest_peak_energy": "Highest peak-energy organism",
    }
    for name, label in labels.items():
        lines.append(label + ":")
        organism = report.notable_organisms[name]
        if organism is None:
            lines.append("  None")
            continue
        lines.extend(
            [
                _kv("Organism ID", str(organism.organism_id), 2),
                _kv("Birth tick", _format_optional(organism.birth_tick), 2),
                _kv("Death tick", _format_optional(organism.death_tick), 2),
                _kv("Longevity (ticks)", _format_count(organism.longevity), 2),
                _kv("Successful eats", _format_count(organism.successful_eats), 2),
                _kv("Energy eaten", f"{organism.energy_eaten:.2f}", 2),
                _kv("Moves", _format_count(organism.moves), 2),
                _kv("Peak energy", f"{organism.peak_energy:.2f}", 2),
                _kv("Final action", organism.final_action or "NONE", 2),
            ]
        )
    lines.extend(["-" * 60, "REPRESENTATIVE LAST-SURVIVOR GENOME"])
    genome = report.representative_genome
    if genome is None:
        lines.append("No organism metrics recorded.")
    else:
        lines.extend(
            [
                _kv("Representative organism ID", str(genome.representative_organism_id)),
                _kv("Longest-longevity IDs", _format_ids(genome.longest_longevity_ids)),
                _kv("Reproduction threshold", f"{genome.reproduction_threshold:.2f}"),
                "",
            ]
        )
        for action in Action:
            lines.append(action.name + ":")
            for sensor, weight in genome.weights[action.name].items():
                lines.append(f"  {sensor:<15}: {weight:6.2f}")
            lines.append("")
    lines.append("=" * 60)
    return "\n".join(lines)
