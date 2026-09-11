from dataclasses import asdict, dataclass
from typing import Mapping

from domain.simulation_config import SimulationConfig
from experiments.configuration import (
    BASELINE_CONFIG,
    EXPERIMENT_FIELD_NAMES,
    build_experiment_config,
)


@dataclass(frozen=True)
class ExperimentFormField:
    name: str
    label: str
    kind: str
    step: str
    minimum: str | None
    help_text: str
    section: str


FORM_FIELDS = (
    ExperimentFormField(
        "seed", "Random Seed", "number", "1", None,
        "Reusing a seed makes identical configurations deterministic.",
        "Run",
    ),
    ExperimentFormField(
        "max_ticks", "Max Ticks", "number", "1", "1",
        "The run stops at this tick unless the population becomes extinct.",
        "Run",
    ),
    ExperimentFormField(
        "world_width", "World Width", "number", "1", "1",
        "Number of cells across the simulated world.", "World",
    ),
    ExperimentFormField(
        "world_height", "World Height", "number", "1", "1",
        "Number of cells down the simulated world.", "World",
    ),
    ExperimentFormField(
        "initial_organisms", "Initial Population", "number", "1", "0",
        "Organisms placed into the world at tick zero.", "Population",
    ),
    ExperimentFormField(
        "initial_organism_energy", "Initial Organism Energy", "number",
        "any", "0", "Starting stored energy for each organism.",
        "Population",
    ),
    ExperimentFormField(
        "regeneration_cell_count", "Regeneration Cell Count", "number",
        "1", "0", "Distinct cells selected for regeneration each tick.",
        "Environment",
    ),
    ExperimentFormField(
        "regeneration_amount", "Regeneration Amount", "number", "any", "0",
        "Energy offered to each selected regeneration cell.", "Environment",
    ),
    ExperimentFormField(
        "initial_reproduction_threshold", "Reproduction Threshold",
        "number", "any", "0",
        "Stored energy at which an organism attempts division.",
        "Population",
    ),
    ExperimentFormField(
        "mutation_rate", "Mutation Rate", "number", "any", "0",
        "Probability that each neural weight mutates at birth (0–1).",
        "Mutation",
    ),
    ExperimentFormField(
        "mutation_amount", "Mutation Amount", "number", "any", "0",
        "Maximum magnitude of a mutation to a neural weight.", "Mutation",
    ),
)

INTEGER_FIELDS = {
    "seed",
    "max_ticks",
    "world_width",
    "world_height",
    "initial_organisms",
    "regeneration_cell_count",
}


@dataclass(frozen=True)
class ExperimentFormResult:
    config: SimulationConfig | None
    values: dict[str, str]
    errors: dict[str, str]


def config_form_values(config: SimulationConfig) -> dict[str, str]:
    config_values = asdict(config)
    return {
        name: str(config_values[name]) for name in EXPERIMENT_FIELD_NAMES
    }


def parse_experiment_form(values: Mapping[str, str]) -> ExperimentFormResult:
    display_values = {
        name: str(values.get(name, "")).strip()
        for name in EXPERIMENT_FIELD_NAMES
    }
    parsed: dict[str, int | float] = {}
    errors: dict[str, str] = {}

    for field in FORM_FIELDS:
        raw_value = display_values[field.name]
        if not raw_value:
            errors[field.name] = "This field is required."
            continue
        try:
            parsed[field.name] = (
                int(raw_value)
                if field.name in INTEGER_FIELDS
                else float(raw_value)
            )
        except ValueError:
            expected = "a whole number" if field.name in INTEGER_FIELDS else "a number"
            errors[field.name] = f"Enter {expected}."

    if errors:
        return ExperimentFormResult(None, display_values, errors)

    try:
        config = build_experiment_config(**parsed)
    except ValueError as exc:
        message = str(exc)
        matching_field = next(
            (name for name in EXPERIMENT_FIELD_NAMES if name in message),
            "form",
        )
        errors[matching_field] = message
        return ExperimentFormResult(None, display_values, errors)

    return ExperimentFormResult(config, display_values, {})


BASELINE_FORM_VALUES = config_form_values(BASELINE_CONFIG)
