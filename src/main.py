import argparse
from collections.abc import Sequence
from datetime import datetime, timezone
import os

from dotenv import load_dotenv

from domain.simulation import Simulation
from domain.simulation_config import SimulationConfig
from domain.action import Action
from domain.simulation_metrics import TickMetrics
from experiments.results import build_experiment_result
from persistence.database import (
    DatabaseConfigurationError,
    PROJECT_ROOT,
    ExperimentDatabase,
    database_name_from_connection_info,
)
from persistence.experiment_recorder import ExperimentRecorder
from persistence.git_info import GitInfo, get_git_info


DEFAULT_SEED = 4
DATABASE_URL_ENVIRONMENT_VARIABLE = "DATABASE_URL"


def parse_args(args: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run an Evolution Toy Universe experiment.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help=f"random seed for the experiment (default: {DEFAULT_SEED})",
    )
    parser.add_argument(
        "--no-persist",
        action="store_true",
        help="run without creating or writing an experiment database",
    )
    return parser.parse_args(args)


def get_database_url() -> str:
    database_url = os.environ.get(DATABASE_URL_ENVIRONMENT_VARIABLE)
    if database_url is None or not database_url.strip():
        raise DatabaseConfigurationError(
            f"{DATABASE_URL_ENVIRONMENT_VARIABLE} must be set when "
            "persistence is enabled"
        )
    return database_url


def should_print_progress(
    tick_metrics: TickMetrics,
    progress_interval: int,
) -> bool:
    return (
        tick_metrics.tick == 1
        or tick_metrics.tick % progress_interval == 0
        or tick_metrics.births > 0
        or tick_metrics.ending_population == 0
    )


def persist_completed_experiment(
    simulation: Simulation,
    started_at: datetime,
    git_info: GitInfo,
    database_url: str,
) -> int:
    experiment_result = build_experiment_result(
        simulation=simulation,
        started_at=started_at,
        git_commit=git_info.commit_hash,
        git_dirty=git_info.dirty,
    )
    database = ExperimentDatabase(database_url)
    database.initialize()
    return ExperimentRecorder(database).save(experiment_result)


def main(args: Sequence[str] | None = None) -> None:
    load_dotenv(PROJECT_ROOT / ".env", override=False)
    options = parse_args(args)

    config = SimulationConfig(
        seed=options.seed,
        world_width=40,
        world_height=40,
        initial_organisms=100,
        initial_organism_energy=100.0,
        minimum_cell_energy=0,
        maximum_cell_energy=10,
        minimum_initial_weight=-1.0,
        maximum_initial_weight=1.0,
        base_energy_cost_per_tick=1.0,
        wait_energy_cost=0.00,
        eat_energy_cost=0.25,
        turn_left_energy_cost=0.50,
        turn_right_energy_cost=0.50,
        move_forward_energy_cost=1.00,
        initial_reproduction_threshold=150.0,
        reproduction_energy_cost=0.0,
    )

    started_at = None
    git_info = None
    database_url = None
    if not options.no_persist:
        database_url = get_database_url()
        started_at = datetime.now(timezone.utc)
        git_info = get_git_info(PROJECT_ROOT)

    simulation = Simulation.big_bang(config)

    maximum_ticks = 10_000
    progress_interval = 10

    while (
        simulation.organisms
        and simulation.tick < maximum_ticks
    ):
        tick_metrics = simulation.step()

        if should_print_progress(tick_metrics, progress_interval):
            print(
                f"Tick {tick_metrics.tick:<5}"
                f"| Population {tick_metrics.ending_population:<4} "
                f"| Births {tick_metrics.births:<3} "
                f"| Deaths {tick_metrics.deaths:<3} "
                f"| Ate {tick_metrics.energy_eaten:8.2f} "
                f"| Moves {tick_metrics.action_counts[Action.MOVE_FORWARD]}"
            )

    simulation.print_experiment_report()

    if not options.no_persist:
        if (
            started_at is None
            or git_info is None
            or database_url is None
        ):
            raise RuntimeError("Missing experiment provenance")
        run_id = persist_completed_experiment(
            simulation=simulation,
            started_at=started_at,
            git_info=git_info,
            database_url=database_url,
        )
        database_name = database_name_from_connection_info(database_url)
        print(
            f"Saved experiment run {run_id} to PostgreSQL database "
            f"{database_name}"
        )


if __name__ == "__main__":
    main()
