import pytest

from domain.simulation_config import SimulationConfig


@pytest.fixture
def config_factory():
    def build(**overrides) -> SimulationConfig:
        values = {
            "seed": 1,
            "world_width": 5,
            "world_height": 5,
            "initial_organisms": 1,
            "initial_organism_energy": 100.0,
            "minimum_cell_energy": 0,
            "maximum_cell_energy": 1,
            "minimum_initial_weight": -1.0,
            "maximum_initial_weight": 1.0,
            "base_energy_cost_per_tick": 0.0,
            "wait_energy_cost": 0.0,
            "eat_energy_cost": 0.0,
            "turn_left_energy_cost": 0.0,
            "turn_right_energy_cost": 0.0,
            "move_forward_energy_cost": 0.0,
            "initial_reproduction_threshold": 90.0,
            "reproduction_energy_cost": 0.0,
        }
        values.update(overrides)
        return SimulationConfig(**values)

    return build

