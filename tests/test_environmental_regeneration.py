import math

import pytest

from domain.action import Action
from domain.sensor import Sensor
from domain.simulation import Simulation


def force_action(organism, selected_action: Action) -> None:
    for action in Action:
        for sensor in Sensor:
            organism.genome.weights[action][sensor] = 0.0
    organism.genome.weights[selected_action][Sensor.BIAS] = 1.0


def make_simulation(config_factory, **overrides) -> Simulation:
    values = {
        "seed": 17,
        "world_width": 4,
        "world_height": 3,
        "initial_organisms": 0,
        "minimum_cell_energy": 0,
        "maximum_cell_energy": 10,
        "regeneration_cell_count": 5,
        "regeneration_amount": 3.0,
    }
    values.update(overrides)
    simulation = Simulation.big_bang(config_factory(**values))
    for cell in simulation.world.cells:
        cell.energy = 0.0
    simulation.initial_world_energy = 0.0
    return simulation


def test_fixed_seed_selects_the_same_distinct_cells(config_factory):
    first = make_simulation(config_factory)
    second = make_simulation(config_factory)

    first_result = first.regenerate_environmental_energy()
    second_result = second.regenerate_environmental_energy()

    assert first_result.selected_cell_indices == (
        second_result.selected_cell_indices
    )
    assert len(first_result.selected_cell_indices) == 5
    assert len(set(first_result.selected_cell_indices)) == 5


def test_regeneration_caps_cells_and_records_wasted_energy(config_factory):
    simulation = make_simulation(
        config_factory,
        world_width=2,
        world_height=2,
        regeneration_cell_count=4,
        regeneration_amount=3.0,
    )
    starting_energy = [9.0, 10.0, 0.0, 8.0]
    for cell, energy in zip(simulation.world.cells, starting_energy):
        cell.energy = energy

    result = simulation.regenerate_environmental_energy()

    assert [cell.energy for cell in simulation.world.cells] == [
        10.0,
        10.0,
        3.0,
        10.0,
    ]
    assert result.attempted_energy == 12.0
    assert result.actual_energy_added == 6.0
    assert result.wasted_energy == 6.0


def test_zero_cell_regeneration_changes_no_state_or_randomness(
    config_factory,
):
    simulation = make_simulation(
        config_factory,
        regeneration_cell_count=0,
        regeneration_amount=3.0,
    )
    random_state = simulation.random.getstate()
    energy_before = [cell.energy for cell in simulation.world.cells]

    result = simulation.regenerate_environmental_energy()

    assert result.selected_cell_indices == ()
    assert result.attempted_energy == 0.0
    assert result.actual_energy_added == 0.0
    assert result.wasted_energy == 0.0
    assert simulation.random.getstate() == random_state
    assert [cell.energy for cell in simulation.world.cells] == energy_before


def test_zero_amount_consumes_no_rng_and_matches_disabled_trajectory(
    config_factory,
):
    zero_amount = make_simulation(
        config_factory,
        seed=23,
        world_width=5,
        world_height=5,
        initial_organisms=3,
        regeneration_cell_count=5,
        regeneration_amount=0.0,
        initial_reproduction_threshold=1_000.0,
    )
    disabled = make_simulation(
        config_factory,
        seed=23,
        world_width=5,
        world_height=5,
        initial_organisms=3,
        regeneration_cell_count=0,
        regeneration_amount=3.0,
        initial_reproduction_threshold=1_000.0,
    )
    random_state = zero_amount.random.getstate()

    result = zero_amount.regenerate_environmental_energy()

    assert result.selected_cell_indices == ()
    assert result.attempted_energy == 0.0
    assert result.actual_energy_added == 0.0
    assert result.wasted_energy == 0.0
    assert zero_amount.random.getstate() == random_state
    assert zero_amount.random.getstate() == disabled.random.getstate()

    for _ in range(20):
        zero_amount.step()
        disabled.step()

    assert zero_amount.random.getstate() == disabled.random.getstate()
    assert [cell.energy for cell in zero_amount.world.cells] == [
        cell.energy for cell in disabled.world.cells
    ]
    assert [
        (
            organism.organism_id,
            organism.x,
            organism.y,
            organism.direction,
            organism.energy,
        )
        for organism in zero_amount.organisms
    ] == [
        (
            organism.organism_id,
            organism.x,
            organism.y,
            organism.direction,
            organism.energy,
        )
        for organism in disabled.organisms
    ]
    assert zero_amount.metrics.action_counts == disabled.metrics.action_counts


def test_amount_above_cell_maximum_is_capped_and_wasted(config_factory):
    simulation = make_simulation(
        config_factory,
        world_width=2,
        world_height=1,
        regeneration_cell_count=2,
        regeneration_amount=25.0,
    )
    simulation.world.cells[1].energy = 9.0

    result = simulation.regenerate_environmental_energy()

    assert [cell.energy for cell in simulation.world.cells] == [10.0, 10.0]
    assert result.attempted_energy == 50.0
    assert result.actual_energy_added == 11.0
    assert result.wasted_energy == 39.0


def test_regenerated_energy_is_available_only_after_action_phase(
    config_factory,
):
    simulation = make_simulation(
        config_factory,
        world_width=1,
        world_height=1,
        initial_organisms=1,
        regeneration_cell_count=1,
        regeneration_amount=3.0,
        initial_reproduction_threshold=1_000.0,
    )
    organism = simulation.organisms[0]
    force_action(organism, Action.EAT)

    first_tick = simulation.step()

    assert first_tick.successful_eats == 0
    assert first_tick.unsuccessful_eats == 1
    assert first_tick.energy_eaten == 0.0
    assert first_tick.regeneration_cells_selected == 1
    assert first_tick.regeneration_energy_attempted == 3.0
    assert first_tick.regeneration_energy_added == 3.0
    assert first_tick.regeneration_energy_wasted == 0.0
    assert simulation.world.cells[0].energy == 3.0

    second_tick = simulation.step()

    assert second_tick.successful_eats == 1
    assert second_tick.energy_eaten == 3.0
    assert second_tick.regeneration_energy_added == 3.0
    assert simulation.world.cells[0].energy == 3.0
    assert simulation.metrics.regeneration_energy_attempted == 6.0
    assert simulation.metrics.regeneration_energy_added == 6.0
    assert simulation.metrics.regeneration_energy_wasted == 0.0
    simulation._run_consistency_checks()


def test_regeneration_replays_deterministically(config_factory):
    simulations = []
    for _ in range(2):
        simulation = make_simulation(
            config_factory,
            seed=91,
            world_width=5,
            world_height=5,
            initial_organisms=3,
            regeneration_cell_count=7,
            regeneration_amount=2.5,
            initial_reproduction_threshold=1_000.0,
        )
        for _ in range(20):
            simulation.step()
        simulations.append(simulation)

    def snapshot(simulation):
        return (
            tuple(cell.energy for cell in simulation.world.cells),
            tuple(
                (
                    organism.organism_id,
                    organism.x,
                    organism.y,
                    organism.direction,
                    organism.energy,
                )
                for organism in simulation.organisms
            ),
            tuple(
                (
                    tick.regeneration_cells_selected,
                    tick.regeneration_energy_attempted,
                    tick.regeneration_energy_added,
                    tick.regeneration_energy_wasted,
                )
                for tick in simulation.metrics.tick_history
            ),
        )

    assert snapshot(simulations[0]) == snapshot(simulations[1])
    assert all(
        cell.energy <= simulations[0].config.maximum_cell_energy
        for cell in simulations[0].world.cells
    )
    simulations[0]._run_consistency_checks()
    simulations[1]._run_consistency_checks()


@pytest.mark.parametrize("cell_count", [-1, 26])
def test_regeneration_cell_count_must_fit_world(
    config_factory,
    cell_count,
):
    with pytest.raises(ValueError, match="regeneration_cell_count"):
        config_factory(regeneration_cell_count=cell_count)


@pytest.mark.parametrize("cell_count", [1.5, True])
def test_regeneration_cell_count_must_be_an_integer(
    config_factory,
    cell_count,
):
    with pytest.raises(ValueError, match="integer"):
        config_factory(regeneration_cell_count=cell_count)


@pytest.mark.parametrize("amount", [-0.1, math.inf, -math.inf, math.nan])
def test_regeneration_amount_must_be_finite_and_nonnegative(
    config_factory,
    amount,
):
    with pytest.raises(ValueError, match="regeneration_amount"):
        config_factory(regeneration_amount=amount)
