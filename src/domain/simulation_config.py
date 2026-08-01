from dataclasses import dataclass


@dataclass(frozen=True)
class SimulationConfig:
    seed: int
    world_width: int
    world_height: int
    initial_organisms: int
    initial_organism_energy: float
    minimum_cell_energy: int
    maximum_cell_energy: int
    minimum_initial_weight: float = -1.0
    maximum_initial_weight: float = 1.0
    base_energy_cost_per_tick: float = 1.0