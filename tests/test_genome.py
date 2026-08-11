import random

from domain.action import Action
from domain.genome import Genome
from domain.sensor import Sensor


def test_random_genome_receives_reproduction_threshold():
    genome = Genome.random_genome(
        random_generator=random.Random(1),
        reproduction_threshold=150.0,
    )

    assert genome.reproduction_threshold == 150.0


def test_genome_copy_is_deep_for_nested_weights():
    weights = {
        action: {
            sensor: float(action_index + sensor_index)
            for sensor_index, sensor in enumerate(Sensor)
        }
        for action_index, action in enumerate(Action)
    }
    parent = Genome(
        weights=weights,
        reproduction_threshold=150.0,
    )

    child = parent.copy()

    assert child is not parent
    assert child.weights == parent.weights
    assert child.weights is not parent.weights
    assert child.reproduction_threshold == parent.reproduction_threshold
    for action in Action:
        assert child.weights[action] is not parent.weights[action]

    child.weights[Action.WAIT][Sensor.BIAS] = 999.0
    assert parent.weights[Action.WAIT][Sensor.BIAS] != 999.0

