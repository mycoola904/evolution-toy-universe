from dataclasses import asdict, dataclass
from types import MappingProxyType
from typing import Mapping

from domain.simulation_config import SimulationConfig


EXPERIMENT_FIELD_NAMES = (
    "seed",
    "max_ticks",
    "world_width",
    "world_height",
    "initial_organisms",
    "initial_organism_energy",
    "regeneration_cell_count",
    "regeneration_amount",
    "initial_reproduction_threshold",
    "mutation_rate",
    "mutation_amount",
)


BASELINE_CONFIG = SimulationConfig(
    seed=4,
    world_width=40,
    world_height=40,
    initial_organisms=100,
    initial_organism_energy=100.0,
    minimum_cell_energy=0,
    maximum_cell_energy=10,
    regeneration_cell_count=45,
    regeneration_amount=3.0,
    minimum_initial_weight=-1.0,
    maximum_initial_weight=1.0,
    base_energy_cost_per_tick=1.0,
    wait_energy_cost=0.00,
    eat_energy_cost=0.25,
    turn_left_energy_cost=0.50,
    turn_right_energy_cost=0.50,
    move_forward_energy_cost=1.00,
    initial_reproduction_threshold=150.0,
    reproduction_energy_cost=0.0,
    mutation_rate=0.01,
    mutation_amount=0.10,
    max_ticks=10_000,
)


@dataclass(frozen=True)
class ExperimentPreset:
    slug: str
    name: str
    description: str
    overrides: Mapping[str, int | float]

    def config(self) -> SimulationConfig:
        return build_experiment_config(**self.overrides)

    def form_values(self) -> dict[str, int | float]:
        values = asdict(self.config())
        return {name: values[name] for name in EXPERIMENT_FIELD_NAMES}


def build_experiment_config(**overrides: int | float) -> SimulationConfig:
    values = asdict(BASELINE_CONFIG)
    values.update(overrides)
    return SimulationConfig(**values)


# Presets vary only experiment-facing controls. All low-level model settings
# retain the values in BASELINE_CONFIG.
PRESETS = (
    ExperimentPreset(
        "baseline",
        "Baseline",
        "The standard ETU experiment used by the command line runner.",
        MappingProxyType({}),
    ),
    ExperimentPreset(
        "scarce",
        "Scarce",
        "Less starting and regenerated energy tests survival under pressure.",
        MappingProxyType(
            {
                "initial_organism_energy": 75.0,
                "regeneration_cell_count": 20,
                "regeneration_amount": 1.0,
            }
        ),
    ),
    ExperimentPreset(
        "lush",
        "Lush",
        "More starting energy and regeneration create an abundant world.",
        MappingProxyType(
            {
                "initial_organism_energy": 125.0,
                "regeneration_cell_count": 90,
                "regeneration_amount": 6.0,
            }
        ),
    ),
    ExperimentPreset(
        "high-mutation",
        "High Mutation",
        "Raises mutation probability and magnitude for faster variation.",
        MappingProxyType(
            {"mutation_rate": 0.10, "mutation_amount": 0.25}
        ),
    ),
    ExperimentPreset(
        "long-run",
        "Long Run",
        "Uses the baseline universe with a 50,000 tick ceiling.",
        MappingProxyType({"max_ticks": 50_000}),
    ),
)

PRESETS_BY_SLUG = MappingProxyType(
    {preset.slug: preset for preset in PRESETS}
)
