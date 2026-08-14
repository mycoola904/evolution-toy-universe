import random
import json

import pytest

from domain.action import Action
from domain.genome import Genome
from domain.sensor import Sensor


def make_genome() -> Genome:
    return Genome(
        weights={
            action: {
                sensor: float(action_index + sensor_index)
                for sensor_index, sensor in enumerate(Sensor)
            }
            for action_index, action in enumerate(Action)
        },
        reproduction_threshold=150.0,
    )


def weight_values(genome: Genome) -> tuple[float, ...]:
    return tuple(
        genome.weights[action][sensor]
        for action in Action
        for sensor in Sensor
    )


class TrackingMutationRandom(random.Random):
    def __init__(self):
        super().__init__(0)
        self.random_calls = 0
        self.uniform_calls: list[tuple[float, float]] = []

    def random(self) -> float:
        self.random_calls += 1
        return 0.5

    def uniform(self, lower: float, upper: float) -> float:
        self.uniform_calls.append((lower, upper))
        return upper


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


def test_genome_to_dict_is_complete_and_json_serializable():
    genome = make_genome()

    genome_data = genome.to_dict()

    assert genome_data["reproduction_threshold"] == 150.0
    assert set(genome_data["weights"]) == {
        action.name for action in Action
    }
    for action in Action:
        assert set(genome_data["weights"][action.name]) == {
            sensor.name for sensor in Sensor
        }
    assert json.loads(json.dumps(genome_data)) == genome_data


def test_identical_genomes_have_no_neural_weight_differences():
    parent = make_genome()

    assert parent.neural_weight_difference_count(parent.copy()) == 0


def test_neural_weight_difference_count_counts_exact_positions():
    parent = make_genome()
    child = parent.copy()
    child.weights[Action.WAIT][Sensor.BIAS] += 0.1
    child.weights[Action.EAT][Sensor.CELL_ENERGY] -= 0.2

    assert child.neural_weight_difference_count(parent) == 2


def test_reproduction_threshold_is_not_a_neural_weight_difference():
    parent = make_genome()
    child = Genome(
        weights={
            action: sensor_weights.copy()
            for action, sensor_weights in parent.weights.items()
        },
        reproduction_threshold=999.0,
    )

    assert child.neural_weight_difference_count(parent) == 0


def test_neural_weight_comparison_rejects_incompatible_topology():
    parent = make_genome()
    child = parent.copy()
    del child.weights[Action.WAIT][Sensor.BIAS]

    with pytest.raises(ValueError, match="topology"):
        child.neural_weight_difference_count(parent)


def test_neural_weight_comparison_changes_no_state_or_randomness():
    parent = make_genome()
    child = parent.copy()
    parent_before = parent.to_dict()
    child_before = child.to_dict()
    random_generator = random.Random(99)
    random_state = random_generator.getstate()

    child.neural_weight_difference_count(parent)

    assert parent.to_dict() == parent_before
    assert child.to_dict() == child_before
    assert random_generator.getstate() == random_state


def test_zero_percent_mutation_produces_an_exact_copy():
    parent = make_genome()

    child = parent.mutated_copy(
        random_generator=random.Random(1),
        mutation_rate=0.0,
        mutation_amount=0.1,
    )

    assert child is not parent
    assert child.weights == parent.weights
    assert child.reproduction_threshold == parent.reproduction_threshold


def test_hundred_percent_mutation_sends_every_weight_through_path():
    parent = make_genome()
    tracking_random = TrackingMutationRandom()
    weight_count = len(Action) * len(Sensor)

    child = parent.mutated_copy(
        random_generator=tracking_random,
        mutation_rate=1.0,
        mutation_amount=0.1,
    )

    assert tracking_random.random_calls == weight_count
    assert tracking_random.uniform_calls == [(-0.1, 0.1)] * weight_count
    for parent_weight, child_weight in zip(
        weight_values(parent),
        weight_values(child),
    ):
        assert child_weight == parent_weight + 0.1


def test_mutation_leaves_parent_genome_unchanged():
    parent = make_genome()
    original_parent = parent.to_dict()

    parent.mutated_copy(
        random_generator=random.Random(2),
        mutation_rate=1.0,
        mutation_amount=0.25,
    )

    assert parent.to_dict() == original_parent


def test_mutated_child_nested_weight_dictionaries_are_independent():
    parent = make_genome()
    child = parent.mutated_copy(
        random_generator=random.Random(3),
        mutation_rate=0.0,
        mutation_amount=0.1,
    )

    assert child.weights is not parent.weights
    for action in Action:
        assert child.weights[action] is not parent.weights[action]

    child.weights[Action.WAIT][Sensor.BIAS] = 999.0
    assert parent.weights[Action.WAIT][Sensor.BIAS] != 999.0


def test_mutation_does_not_change_reproduction_threshold():
    parent = make_genome()

    child = parent.mutated_copy(
        random_generator=random.Random(4),
        mutation_rate=1.0,
        mutation_amount=100.0,
    )

    assert child.reproduction_threshold == parent.reproduction_threshold


def test_same_rng_seed_produces_identical_mutations():
    parent = make_genome()

    first_child = parent.mutated_copy(
        random_generator=random.Random(5),
        mutation_rate=0.5,
        mutation_amount=0.2,
    )
    second_child = parent.mutated_copy(
        random_generator=random.Random(5),
        mutation_rate=0.5,
        mutation_amount=0.2,
    )

    assert first_child.to_dict() == second_child.to_dict()


def test_different_rng_seeds_can_produce_different_mutations():
    parent = make_genome()

    first_child = parent.mutated_copy(
        random_generator=random.Random(6),
        mutation_rate=1.0,
        mutation_amount=0.2,
    )
    second_child = parent.mutated_copy(
        random_generator=random.Random(7),
        mutation_rate=1.0,
        mutation_amount=0.2,
    )

    assert first_child.weights != second_child.weights


def test_each_changed_weight_is_within_mutation_amount():
    parent = make_genome()
    mutation_amount = 0.1

    child = parent.mutated_copy(
        random_generator=random.Random(8),
        mutation_rate=1.0,
        mutation_amount=mutation_amount,
    )

    changed_weight_count = 0
    for parent_weight, child_weight in zip(
        weight_values(parent),
        weight_values(child),
    ):
        difference = abs(child_weight - parent_weight)
        if difference > 0.0:
            changed_weight_count += 1
            assert difference <= mutation_amount + 1e-12

    assert changed_weight_count == len(Action) * len(Sensor)

