from dataclasses import dataclass
import math


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
    wait_energy_cost: float = 0.00
    eat_energy_cost: float = 0.25
    turn_left_energy_cost: float = 0.50
    turn_right_energy_cost: float = 0.50
    move_forward_energy_cost: float = 1.00
    initial_reproduction_threshold: float = 150.0
    reproduction_energy_cost: float = 0.0

    def __post_init__(self) -> None:
        reproduction_values = {
            "initial_reproduction_threshold": (
                self.initial_reproduction_threshold
            ),
            "reproduction_energy_cost": self.reproduction_energy_cost,
        }

        for name, value in reproduction_values.items():
            if not math.isfinite(value) or value < 0.0:
                raise ValueError(
                    f"{name} must be finite and nonnegative"
                )
