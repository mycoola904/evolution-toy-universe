from domain.action import Action
from domain.simulation import Simulation
from experiments.report import build_experiment_report, format_experiment_report


def test_structured_report_contains_every_cli_section_and_is_observational(
    config_factory,
):
    simulation = Simulation.big_bang(
        config_factory(
            max_ticks=1,
            minimum_cell_energy=0,
            maximum_cell_energy=1,
            regeneration_cell_count=0,
        )
    )
    simulation.step()
    random_state = simulation.random.getstate()

    report = build_experiment_report(simulation)

    assert simulation.random.getstate() == random_state
    assert report.schema_version == 1
    assert report.summary.final_tick == 1
    assert report.summary.seed == simulation.config.seed
    assert len(report.action_totals) == len(Action)
    assert report.eating.total_eat_attempts == (
        simulation.metrics.action_counts[Action.EAT]
    )
    assert report.movement.total_move_forward_actions == (
        simulation.metrics.action_counts[Action.MOVE_FORWARD]
    )
    assert report.reproduction.total_births == simulation.metrics.total_births
    assert report.survival.longest_lived_organism_ids == (0,)
    assert set(report.notable_organisms) == {
        "longest_lived",
        "largest_energy_consumer",
        "most_mobile",
        "highest_peak_energy",
    }
    assert report.representative_genome is not None
    assert set(report.to_dict()) == {
        "schema_version",
        "summary",
        "environmental_energy",
        "action_totals",
        "eating",
        "movement",
        "reproduction",
        "survival",
        "notable_organisms",
        "representative_genome",
    }


def test_cli_formatter_uses_structured_report_values(config_factory):
    simulation = Simulation.big_bang(
        config_factory(
            max_ticks=1,
            minimum_cell_energy=0,
            maximum_cell_energy=1,
            regeneration_cell_count=0,
        )
    )
    simulation.step()
    report = build_experiment_report(simulation)

    output = format_experiment_report(report)

    assert "EXPERIMENT SUMMARY" in output
    assert f"Seed                                         {report.summary.seed}" in output
    assert "ENVIRONMENTAL ENERGY" in output
    assert "ACTION TOTALS" in output
    assert "EATING RESULTS" in output
    assert "MOVEMENT RESULTS" in output
    assert "REPRODUCTION RESULTS" in output
    assert "SURVIVAL RESULTS" in output
    assert "NOTABLE ORGANISMS" in output
    assert "REPRESENTATIVE LAST-SURVIVOR GENOME" in output


def test_simulation_print_uses_shared_builder_and_formatter(
    config_factory,
    monkeypatch,
    capsys,
):
    import experiments.report as report_module

    simulation = Simulation.big_bang(config_factory())
    sentinel = object()
    monkeypatch.setattr(
        report_module,
        "build_experiment_report",
        lambda value: sentinel,
    )
    monkeypatch.setattr(
        report_module,
        "format_experiment_report",
        lambda value: "structured report",
    )

    simulation.print_experiment_report()

    assert capsys.readouterr().out == "structured report\n"
