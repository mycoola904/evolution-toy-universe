from dataclasses import dataclass

from domain.action import Action
from domain.genome import Genome


def new_action_counts() -> dict[Action, int]:
    return {
        action: 0
        for action in Action
    }


@dataclass
class OrganismMetrics:
    organism_id: int
    genome: Genome
    action_counts: dict[Action, int]
    parent_id: int | None
    birth_tick: int
    mutated_weight_count: int | None
    initial_energy: float
    final_energy: float
    offspring_count: int = 0

    successful_eats: int = 0
    unsuccessful_eats: int = 0
    energy_eaten: float = 0.0

    first_successful_eat_tick: int | None = None
    last_successful_eat_tick: int | None = None

    peak_energy: float = 0.0
    death_tick: int | None = None
    final_action: Action | None = None


@dataclass
class TickMetrics:
    tick: int
    starting_population: int
    action_counts: dict[Action, int]

    ending_population: int = 0
    deaths: int = 0
    births: int = 0

    successful_eats: int = 0
    unsuccessful_eats: int = 0
    energy_eaten: float = 0.0


@dataclass
class SimulationMetrics:
    organism_metrics: dict[int, OrganismMetrics]
    tick_history: list[TickMetrics]
    action_counts: dict[Action, int]

    successful_eats: int = 0
    unsuccessful_eats: int = 0
    total_energy_eaten: float = 0.0

    tick_one_energy_eaten: float = 0.0
    after_tick_one_energy_eaten: float = 0.0

    first_successful_eat_tick: int | None = None
    last_successful_eat_tick: int | None = None

    total_births: int = 0
    first_birth_tick: int | None = None
    last_birth_tick: int | None = None
    peak_population: int = 0
