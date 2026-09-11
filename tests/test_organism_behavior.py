from datetime import datetime, timezone

import pytest

from domain.action import Action
from domain.sensor import Sensor
from domain.simulation import Simulation
from experiments.results import OrganismResult, build_experiment_result


def force_action(organism, selected_action: Action) -> None:
    for action in Action:
        for sensor in Sensor:
            organism.genome.weights[action][sensor] = 0.0
    organism.genome.weights[selected_action][Sensor.BIAS] = 1.0


def test_metrics_and_completed_result_capture_every_action_and_eat_outcome(
    config_factory,
):
    simulation = Simulation.big_bang(
        config_factory(
            max_ticks=6,
            initial_reproduction_threshold=1_000.0,
        )
    )
    organism = simulation.organisms[0]
    for cell in simulation.world.cells:
        cell.energy = 0.0
    simulation.initial_world_energy = 5.0

    force_action(organism, Action.WAIT)
    simulation.step()
    simulation.world.get_cell(organism.x, organism.y).energy = 5.0
    force_action(organism, Action.EAT)
    simulation.step()
    simulation.initial_world_energy = simulation.total_world_energy() + 5.0
    simulation.step()
    for action in (Action.MOVE_FORWARD, Action.TURN_LEFT, Action.TURN_RIGHT):
        force_action(organism, action)
        simulation.step()

    metrics = simulation.metrics.organism_metrics[0]
    assert metrics.action_counts == {
        Action.WAIT: 1,
        Action.EAT: 2,
        Action.MOVE_FORWARD: 1,
        Action.TURN_LEFT: 1,
        Action.TURN_RIGHT: 1,
    }
    assert metrics.successful_eats == 1
    assert metrics.unsuccessful_eats == 1
    assert metrics.final_action is Action.TURN_RIGHT

    result = build_experiment_result(
        simulation,
        datetime(2026, 9, 10, tzinfo=timezone.utc),
        git_commit=None,
        git_dirty=None,
    ).organisms[0]
    assert result.wait_count == 1
    assert result.eat_attempt_count == 2
    assert result.successful_eat_count == 1
    assert result.unsuccessful_eat_count == 1
    assert result.move_forward_count == 1
    assert result.turn_left_count == 1
    assert result.turn_right_count == 1
    assert result.final_action == "TURN_RIGHT"


def result_with_behavior(**overrides):
    values = {
        "organism_id": 0,
        "parent_organism_id": None,
        "birth_tick": 0,
        "mutated_weight_count": None,
        "death_tick": None,
        "lifespan": 5,
        "initial_energy": 100.0,
        "final_energy": 80.0,
        "peak_energy": 110.0,
        "energy_consumed": 10.0,
        "distance_moved": 1,
        "genome": {},
        "wait_count": 1,
        "eat_attempt_count": 1,
        "successful_eat_count": 1,
        "unsuccessful_eat_count": 0,
        "move_forward_count": 1,
        "turn_left_count": 1,
        "turn_right_count": 1,
        "final_action": "TURN_RIGHT",
    }
    values.update(overrides)
    return OrganismResult(**values)


@pytest.mark.parametrize(
    ("overrides", "message"),
    (
        ({"successful_eat_count": 2}, "EATs must equal attempts"),
        ({"wait_count": -1}, "nonnegative"),
        ({"move_forward_count": 2}, "match distance_moved"),
        ({"final_action": "FLY"}, "known action"),
        ({"final_action": None}, "exactly when actions exist"),
    ),
)
def test_completed_result_rejects_inconsistent_behavior(overrides, message):
    with pytest.raises(ValueError, match=message):
        result_with_behavior(**overrides)


def test_completed_result_accepts_zero_action_newborn():
    result = result_with_behavior(
        lifespan=0,
        distance_moved=0,
        wait_count=0,
        eat_attempt_count=0,
        successful_eat_count=0,
        unsuccessful_eat_count=0,
        move_forward_count=0,
        turn_left_count=0,
        turn_right_count=0,
        final_action=None,
    )

    assert result.final_action is None
