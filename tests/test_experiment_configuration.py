from experiment_console.forms import parse_experiment_form
from experiments.configuration import (
    BASELINE_CONFIG,
    EXPERIMENT_FIELD_NAMES,
    PRESETS_BY_SLUG,
)


def baseline_values():
    return PRESETS_BY_SLUG["baseline"].form_values()


def test_presets_are_distinct_and_retain_fixed_model_values():
    assert set(PRESETS_BY_SLUG) == {
        "baseline",
        "scarce",
        "lush",
        "high-mutation",
        "long-run",
    }
    visible = {
        slug: tuple(preset.form_values().values())
        for slug, preset in PRESETS_BY_SLUG.items()
    }
    assert len(set(visible.values())) == 5
    for preset in PRESETS_BY_SLUG.values():
        assert preset.config().eat_energy_cost == BASELINE_CONFIG.eat_energy_cost
        assert preset.config().maximum_cell_energy == 10


def test_form_builds_the_same_simulation_config_with_edited_values():
    values = {name: str(value) for name, value in baseline_values().items()}
    values["seed"] = "91"
    values["mutation_rate"] = "0.2"

    result = parse_experiment_form(values)

    assert result.errors == {}
    assert result.config is not None
    assert result.config.seed == 91
    assert result.config.mutation_rate == 0.2
    assert result.config.base_energy_cost_per_tick == 1.0


def test_form_preserves_values_and_reports_domain_validation():
    values = {name: str(value) for name, value in baseline_values().items()}
    values["world_width"] = "0"

    result = parse_experiment_form(values)

    assert result.config is None
    assert result.values["world_width"] == "0"
    assert "world" in result.errors["form"]


def test_form_requires_every_experiment_field():
    result = parse_experiment_form({})

    assert result.config is None
    assert set(result.errors) == set(EXPERIMENT_FIELD_NAMES)
