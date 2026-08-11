from domain.simulation_metrics import TickMetrics, new_action_counts
from main import should_print_progress


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
