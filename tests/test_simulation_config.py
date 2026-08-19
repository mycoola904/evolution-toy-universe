import math

import pytest

from domain.simulation_config import SimulationConfig


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("initial_reproduction_threshold", -1.0),
        ("initial_reproduction_threshold", math.inf),
        ("initial_reproduction_threshold", -math.inf),
        ("initial_reproduction_threshold", math.nan),
        ("reproduction_energy_cost", -1.0),
        ("reproduction_energy_cost", math.inf),
        ("reproduction_energy_cost", -math.inf),
        ("reproduction_energy_cost", math.nan),
    ],
)
def test_reproduction_configuration_must_be_finite_and_nonnegative(
    config_factory,
    field,
    value,
):
    with pytest.raises(ValueError, match=field):
        config_factory(**{field: value})


def test_reproduction_configuration_defaults():
    config = SimulationConfig(
        seed=1,
        world_width=5,
        world_height=5,
        initial_organisms=1,
        initial_organism_energy=100.0,
        minimum_cell_energy=0,
        maximum_cell_energy=1,
        regeneration_cell_count=0,
        regeneration_amount=0.0,
    )

    assert config.initial_reproduction_threshold == 150.0
    assert config.reproduction_energy_cost == 0.0
    assert config.mutation_rate == 0.01
    assert config.mutation_amount == 0.10
    assert config.max_ticks == 10_000


@pytest.mark.parametrize("max_ticks", [0, -1, 1.5, True])
def test_max_ticks_must_be_a_positive_integer(
    config_factory,
    max_ticks,
):
    with pytest.raises(ValueError, match="max_ticks"):
        config_factory(max_ticks=max_ticks)


def test_max_ticks_can_be_configured(config_factory):
    config = config_factory(max_ticks=25)

    assert config.max_ticks == 25


@pytest.mark.parametrize(
    "mutation_rate",
    [-0.01, 1.01, math.inf, -math.inf, math.nan],
)
def test_mutation_rate_must_be_finite_probability(
    config_factory,
    mutation_rate,
):
    with pytest.raises(ValueError, match="mutation_rate"):
        config_factory(mutation_rate=mutation_rate)


@pytest.mark.parametrize(
    "mutation_amount",
    [-0.01, math.inf, -math.inf, math.nan],
)
def test_mutation_amount_must_be_finite_and_nonnegative(
    config_factory,
    mutation_amount,
):
    with pytest.raises(ValueError, match="mutation_amount"):
        config_factory(mutation_amount=mutation_amount)
