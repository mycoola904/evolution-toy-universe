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
    )

    assert config.initial_reproduction_threshold == 150.0
    assert config.reproduction_energy_cost == 0.0
