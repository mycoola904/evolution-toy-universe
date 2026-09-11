import argparse
from collections.abc import Sequence
from datetime import datetime
import os

from dotenv import load_dotenv

from domain.simulation import Simulation
from domain.simulation_config import SimulationConfig
from domain.action import Action
from domain.simulation_metrics import TickMetrics
from experiments.configuration import BASELINE_CONFIG, build_experiment_config
from experiments.runner import ExperimentRunner
from experiments.results import build_experiment_result
from persistence.database import (
    DatabaseConfigurationError,
    PROJECT_ROOT,
    ExperimentDatabase,
    database_name_from_connection_info,
)
from persistence.experiment_recorder import ExperimentRecorder
from persistence.git_info import GitInfo, get_git_info


DEFAULT_SEED = BASELINE_CONFIG.seed
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
        "--max-ticks",
        type=int,
        default=SimulationConfig.max_ticks,
        help=(
            "maximum simulation ticks for the experiment "
            f"(default: {SimulationConfig.max_ticks})"
        ),
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


def print_progress(tick_metrics: TickMetrics) -> None:
    if not should_print_progress(tick_metrics, progress_interval=10):
        return
    print(
        f"Tick {tick_metrics.tick:<5}"
        f"| Population {tick_metrics.ending_population:<4} "
        f"| Births {tick_metrics.births:<3} "
        f"| Deaths {tick_metrics.deaths:<3} "
        f"| Ate {tick_metrics.energy_eaten:8.2f} "
        f"| Moves {tick_metrics.action_counts[Action.MOVE_FORWARD]}"
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

    config = build_experiment_config(
        seed=options.seed,
        max_ticks=options.max_ticks,
    )

    database_url = None
    if not options.no_persist:
        database_url = get_database_url()

    runner = ExperimentRunner(
        project_root=PROJECT_ROOT,
        simulation_factory=Simulation.big_bang,
        git_info_factory=get_git_info,
        persistence_callback=persist_completed_experiment,
    )
    outcome = runner.run(
        config,
        database_url=database_url,
        persist=not options.no_persist,
        on_tick=print_progress,
    )
    outcome.simulation.print_experiment_report()

    if not options.no_persist:
        if outcome.run_id is None or database_url is None:
            raise RuntimeError("Missing experiment provenance")
        database_name = database_name_from_connection_info(database_url)
        print(
            f"Saved experiment run {outcome.run_id} to PostgreSQL database "
            f"{database_name}"
        )


if __name__ == "__main__":
    main()
