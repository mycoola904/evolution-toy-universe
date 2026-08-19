import psycopg
import pytest

import main as main_module
from domain.simulation_metrics import TickMetrics, new_action_counts
from main import DEFAULT_SEED, parse_args, should_print_progress
from persistence.database import DatabaseConfigurationError
from persistence.git_info import GitInfo


EXAMPLE_DATABASE_URL = (
    "postgresql://experiment_role:not-a-real-password@localhost:5432/"
    "evolution_toy_universe"
)


def test_seed_defaults_to_current_experiment_seed():
    assert parse_args([]).seed == DEFAULT_SEED


def test_seed_can_be_set_from_command_line():
    assert parse_args(["--seed", "123"]).seed == 123


def test_max_ticks_defaults_to_standard_experiment_limit():
    assert parse_args([]).max_ticks == 10_000


def test_max_ticks_can_be_set_from_command_line():
    assert parse_args(["--max-ticks", "100000"]).max_ticks == 100_000


def test_no_persist_option_is_parsed():
    assert parse_args(["--no-persist"]).no_persist is True


def make_tick_metrics(**overrides) -> TickMetrics:
    values = {
        "tick": 2,
        "starting_population": 1,
        "action_counts": new_action_counts(),
        "ending_population": 1,
    }
    values.update(overrides)
    return TickMetrics(**values)


def test_progress_prints_when_birth_occurs():
    tick_metrics = make_tick_metrics(births=1)

    assert should_print_progress(tick_metrics, progress_interval=10)


def test_progress_can_remain_quiet_without_progress_event():
    tick_metrics = make_tick_metrics()

    assert not should_print_progress(
        tick_metrics,
        progress_interval=10,
    )


class CompletedSimulation:
    organisms = []
    tick = 0

    def print_experiment_report(self) -> None:
        pass


class TickLimitedSimulation:
    def __init__(self, extinction_tick: int | None = None) -> None:
        self.organisms = [object()]
        self.tick = 0
        self.extinction_tick = extinction_tick

    def step(self) -> TickMetrics:
        self.tick += 1
        if self.tick == self.extinction_tick:
            self.organisms = []
        return make_tick_metrics(
            tick=self.tick,
            ending_population=len(self.organisms),
        )

    def print_experiment_report(self) -> None:
        pass


def test_run_stops_at_configured_max_ticks(monkeypatch):
    simulation = TickLimitedSimulation()
    monkeypatch.setattr(
        main_module.Simulation,
        "big_bang",
        lambda config: simulation,
    )

    main_module.main(["--max-ticks", "3", "--no-persist"])

    assert simulation.tick == 3


def test_extinction_stops_run_before_configured_max_ticks(monkeypatch):
    simulation = TickLimitedSimulation(extinction_tick=2)
    monkeypatch.setattr(
        main_module.Simulation,
        "big_bang",
        lambda config: simulation,
    )

    main_module.main(["--max-ticks", "5", "--no-persist"])

    assert simulation.tick == 2


def test_no_persist_skips_configuration_git_and_database_work(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    loaded = {}

    def fake_load_dotenv(path, *, override):
        loaded["path"] = path
        loaded["override"] = override

    monkeypatch.setattr(main_module, "load_dotenv", fake_load_dotenv)

    def capture_config(config):
        loaded["config"] = config
        return CompletedSimulation()

    monkeypatch.setattr(
        main_module.Simulation,
        "big_bang",
        capture_config,
    )

    def unexpected_call(*args, **kwargs):
        raise AssertionError("persistence work should have been skipped")

    monkeypatch.setattr(main_module, "get_database_url", unexpected_call)
    monkeypatch.setattr(main_module, "get_git_info", unexpected_call)
    monkeypatch.setattr(
        main_module,
        "persist_completed_experiment",
        unexpected_call,
    )

    main_module.main(["--no-persist"])

    assert loaded["path"] == main_module.PROJECT_ROOT / ".env"
    assert loaded["override"] is False
    assert loaded["config"].regeneration_cell_count == 45
    assert loaded["config"].regeneration_amount == 3.0
    assert loaded["config"].max_ticks == 10_000


def test_persistence_requires_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(
        main_module,
        "load_dotenv",
        lambda path, *, override: False,
    )

    with pytest.raises(
        DatabaseConfigurationError,
        match="DATABASE_URL must be set",
    ):
        main_module.main([])


def test_normal_run_persists_to_configured_database(
    monkeypatch,
    capsys,
):
    captured = {}
    monkeypatch.setenv("DATABASE_URL", EXAMPLE_DATABASE_URL)
    monkeypatch.setattr(
        main_module.Simulation,
        "big_bang",
        lambda config: CompletedSimulation(),
    )
    monkeypatch.setattr(
        main_module,
        "get_git_info",
        lambda path: GitInfo("abc123", False),
    )

    def fake_persist(**kwargs):
        captured.update(kwargs)
        return 7

    monkeypatch.setattr(
        main_module,
        "persist_completed_experiment",
        fake_persist,
    )

    main_module.main([])

    output = capsys.readouterr().out
    assert captured["database_url"] == EXAMPLE_DATABASE_URL
    assert captured["git_info"] == GitInfo("abc123", False)
    assert "Saved experiment run 7" in output
    assert "evolution_toy_universe" in output
    assert "not-a-real-password" not in output


def test_persistence_failure_is_fatal(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", EXAMPLE_DATABASE_URL)
    monkeypatch.setattr(
        main_module.Simulation,
        "big_bang",
        lambda config: CompletedSimulation(),
    )
    monkeypatch.setattr(
        main_module,
        "get_git_info",
        lambda path: GitInfo(None, None),
    )

    def fail(**kwargs):
        raise psycopg.OperationalError("database unavailable")

    monkeypatch.setattr(
        main_module,
        "persist_completed_experiment",
        fail,
    )

    with pytest.raises(
        psycopg.OperationalError,
        match="database unavailable",
    ):
        main_module.main([])
