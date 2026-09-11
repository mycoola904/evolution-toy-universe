from datetime import datetime, timezone

from domain.simulation_metrics import TickMetrics, new_action_counts
from experiments.configuration import build_experiment_config
from experiments.runner import ExperimentRunner
from persistence.git_info import GitInfo


class FakeSimulation:
    def __init__(self, extinction_tick=None):
        self.tick = 0
        self.organisms = [object()]
        self.extinction_tick = extinction_tick

    def step(self):
        self.tick += 1
        if self.tick == self.extinction_tick:
            self.organisms = []
        return TickMetrics(
            tick=self.tick,
            starting_population=1,
            ending_population=len(self.organisms),
            action_counts=new_action_counts(),
        )


def test_runner_executes_to_tick_limit_and_reports_each_tick():
    simulation = FakeSimulation()
    observed_ticks = []
    runner = ExperimentRunner(
        simulation_factory=lambda config: simulation,
        git_info_factory=lambda path: (_ for _ in ()).throw(
            AssertionError("git should not be inspected")
        ),
    )

    outcome = runner.run(
        build_experiment_config(max_ticks=3),
        persist=False,
        on_tick=lambda metrics: observed_ticks.append(metrics.tick),
    )

    assert outcome.simulation is simulation
    assert outcome.run_id is None
    assert simulation.tick == 3
    assert observed_ticks == [1, 2, 3]


def test_runner_stops_on_extinction_and_persists_once(tmp_path):
    simulation = FakeSimulation(extinction_tick=2)
    captured = {}
    started_at = datetime(2026, 9, 10, tzinfo=timezone.utc)

    def persist(**kwargs):
        captured.update(kwargs)
        return 17

    runner = ExperimentRunner(
        project_root=tmp_path,
        simulation_factory=lambda config: simulation,
        git_info_factory=lambda path: GitInfo("abc123", False),
        persistence_callback=persist,
        clock=lambda: started_at,
    )

    outcome = runner.run(
        build_experiment_config(max_ticks=50),
        database_url="postgresql://example/db",
    )

    assert simulation.tick == 2
    assert outcome.run_id == 17
    assert captured == {
        "simulation": simulation,
        "started_at": started_at,
        "git_info": GitInfo("abc123", False),
        "database_url": "postgresql://example/db",
    }
