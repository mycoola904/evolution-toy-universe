from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from domain.simulation import Simulation
from domain.simulation_config import SimulationConfig
from domain.simulation_metrics import TickMetrics
from experiments.results import build_experiment_result
from persistence.database import ExperimentDatabase, PROJECT_ROOT
from persistence.experiment_recorder import ExperimentRecorder
from persistence.git_info import GitInfo, get_git_info


@dataclass(frozen=True)
class ExperimentRunOutcome:
    simulation: Simulation
    run_id: int | None


class ExperimentRunner:
    """Run one experiment independently of any CLI or web framework."""

    def __init__(
        self,
        *,
        project_root: Path = PROJECT_ROOT,
        simulation_factory: Callable[[SimulationConfig], Simulation] = (
            Simulation.big_bang
        ),
        git_info_factory: Callable[[Path], GitInfo] = get_git_info,
        persistence_callback: Callable[..., int] | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.project_root = project_root
        self.simulation_factory = simulation_factory
        self.git_info_factory = git_info_factory
        self.persistence_callback = persistence_callback
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def run(
        self,
        config: SimulationConfig,
        *,
        database_url: str | None = None,
        persist: bool = True,
        on_tick: Callable[[TickMetrics], None] | None = None,
    ) -> ExperimentRunOutcome:
        started_at = self.clock() if persist else None
        git_info = (
            self.git_info_factory(self.project_root) if persist else None
        )
        simulation = self.simulation_factory(config)

        while simulation.organisms and simulation.tick < config.max_ticks:
            tick_metrics = simulation.step()
            if on_tick is not None:
                on_tick(tick_metrics)

        run_id = None
        if persist:
            if database_url is None or not database_url.strip():
                raise ValueError(
                    "database_url is required when persistence is enabled"
                )
            if started_at is None or git_info is None:
                raise RuntimeError("Missing experiment provenance")
            run_id = self._persist(
                simulation=simulation,
                started_at=started_at,
                git_info=git_info,
                database_url=database_url,
            )

        return ExperimentRunOutcome(simulation=simulation, run_id=run_id)

    def _persist(
        self,
        *,
        simulation: Simulation,
        started_at: datetime,
        git_info: GitInfo,
        database_url: str,
    ) -> int:
        if self.persistence_callback is not None:
            return self.persistence_callback(
                simulation=simulation,
                started_at=started_at,
                git_info=git_info,
                database_url=database_url,
            )

        result = build_experiment_result(
            simulation=simulation,
            started_at=started_at,
            git_commit=git_info.commit_hash,
            git_dirty=git_info.dirty,
        )
        database = ExperimentDatabase(database_url)
        database.initialize()
        return ExperimentRecorder(database).save(result)
