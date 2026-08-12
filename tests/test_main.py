import pytest

import main as main_module
from domain.simulation_metrics import TickMetrics, new_action_counts
from main import DEFAULT_SEED, parse_args, should_print_progress
from persistence.git_info import GitInfo


def test_seed_defaults_to_current_experiment_seed():
    assert parse_args([]).seed == DEFAULT_SEED


def test_seed_can_be_set_from_command_line():
    assert parse_args(["--seed", "123"]).seed == 123


def test_database_and_no_persist_options_are_parsed(tmp_path):
    database_path = tmp_path / "alternate.db"

    options = parse_args(
        ["--database", str(database_path), "--no-persist"]
    )

    assert options.database == database_path
    assert options.no_persist is True


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


def test_no_persist_skips_git_and_database_work(monkeypatch, tmp_path):
    database_path = tmp_path / "nested" / "experiments.db"
    monkeypatch.setattr(
        main_module.Simulation,
        "big_bang",
        lambda config: CompletedSimulation(),
    )

    def unexpected_call(*args, **kwargs):
        raise AssertionError("persistence work should have been skipped")

    monkeypatch.setattr(main_module, "get_git_info", unexpected_call)
    monkeypatch.setattr(
        main_module,
        "persist_completed_experiment",
        unexpected_call,
    )

    main_module.main(
        ["--no-persist", "--database", str(database_path)]
    )

    assert not database_path.exists()
    assert not database_path.parent.exists()


def test_normal_run_persists_to_selected_database(
    monkeypatch,
    tmp_path,
    capsys,
):
    database_path = tmp_path / "experiments.db"
    captured = {}
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

    main_module.main(["--database", str(database_path)])

    assert captured["database_path"] == database_path
    assert captured["git_info"] == GitInfo("abc123", False)
    assert "Saved experiment run 7" in capsys.readouterr().out


def test_persistence_failure_is_fatal(monkeypatch, tmp_path):
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
        raise OSError("database unavailable")

    monkeypatch.setattr(
        main_module,
        "persist_completed_experiment",
        fail,
    )

    with pytest.raises(OSError, match="database unavailable"):
        main_module.main(
            ["--database", str(tmp_path / "experiments.db")]
        )
