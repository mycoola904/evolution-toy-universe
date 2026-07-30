from dataclasses import dataclass


@dataclass(frozen=True)
class SimulationConfig:
    seed: int
    world_width: int
    world_height: int
    initial_organisms: int
    minimum_cell_energy: int
    maximum_cell_energy: int