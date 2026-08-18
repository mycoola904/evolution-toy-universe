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
    regeneration_cell_count: int
    regeneration_amount: float
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
    mutation_rate: float = 0.01
    mutation_amount: float = 0.10

    def __post_init__(self) -> None:
        total_cells = self.world_width * self.world_height
        if type(self.regeneration_cell_count) is not int:
            raise ValueError("regeneration_cell_count must be an integer")
        if not 0 <= self.regeneration_cell_count <= total_cells:
            raise ValueError(
                "regeneration_cell_count must be between 0 and the "
                "total number of world cells"
            )

        if (
            not math.isfinite(self.regeneration_amount)
            or self.regeneration_amount < 0.0
        ):
            raise ValueError(
                "regeneration_amount must be finite and nonnegative"
            )

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

        if not (0.0 <= self.mutation_rate <= 1.0):
            raise ValueError(
                "mutation_rate must be between 0.0 and 1.0"
            )

        if (
            not math.isfinite(self.mutation_amount)
            or self.mutation_amount < 0.0
        ):
            raise ValueError(
                "mutation_amount must be finite and nonnegative"
            )
