from domain.action import Action
from domain.direction import Direction
from domain.genome import Genome
from domain.sensor import Sensor
from domain.simulation import Simulation


def force_action(organism, selected_action: Action) -> None:
    for action in Action:
        for sensor in Sensor:
            organism.genome.weights[action][sensor] = 0.0
    organism.genome.weights[selected_action][Sensor.BIAS] = 1.0


def zero_world_energy(simulation: Simulation) -> None:
    for cell in simulation.world.cells:
        cell.energy = 0.0
    simulation.initial_world_energy = 0.0


def make_weights() -> dict[Action, dict[Sensor, float]]:
    return {
        action: {sensor: 0.0 for sensor in Sensor}
        for action in Action
    }


def test_forced_reproduction_tracks_lineage_and_delays_child_action(
    config_factory,
):
    simulation = Simulation.big_bang(config_factory())
    zero_world_energy(simulation)
    parent = simulation.organisms[0]
    force_action(parent, Action.WAIT)
    parent_direction = parent.direction

    tick_one = simulation.step()

    assert tick_one.births == 1
    assert tick_one.deaths == 0
    assert tick_one.ending_population == 2
    assert simulation.metrics.total_births == 1
    assert simulation.metrics.first_birth_tick == 1
    assert simulation.metrics.last_birth_tick == 1
    assert simulation.metrics.peak_population == 2

    parent = next(
        organism
        for organism in simulation.organisms
        if organism.organism_id == 0
    )
    child = next(
        organism
        for organism in simulation.organisms
        if organism.organism_id != 0
    )
    parent_metrics = simulation.metrics.organism_metrics[
        parent.organism_id
    ]
    child_metrics = simulation.metrics.organism_metrics[
        child.organism_id
    ]

    assert child.organism_id != parent.organism_id
    assert child.parent_id == parent.organism_id
    assert child.birth_tick == 1
    assert parent.birth_tick == 0
    assert child_metrics.parent_id == parent.organism_id
    assert child_metrics.birth_tick == 1
    assert parent_metrics.birth_tick == 0
    assert parent_metrics.offspring_count == 1
    assert child.direction == parent_direction
    assert parent.energy == child.energy == 50.0
    assert child.genome.weights == parent.genome.weights
    assert child.genome is not parent.genome
    assert child.genome.weights is not parent.genome.weights
    assert sum(child_metrics.action_counts.values()) == 0

    simulation.step()
    assert sum(child_metrics.action_counts.values()) == 1
    simulation._run_consistency_checks()


def test_reproduction_cost_is_conserved(config_factory):
    simulation = Simulation.big_bang(
        config_factory(reproduction_energy_cost=10.0)
    )
    zero_world_energy(simulation)
    force_action(simulation.organisms[0], Action.WAIT)

    tick_metrics = simulation.step()

    assert tick_metrics.births == 1
    energies = sorted(
        organism.energy for organism in simulation.organisms
    )
    assert energies == [45.0, 45.0]
    assert sum(energies) == 100.0 - 10.0


def test_parent_that_cannot_afford_cost_keeps_energy(config_factory):
    simulation = Simulation.big_bang(
        config_factory(reproduction_energy_cost=110.0)
    )
    zero_world_energy(simulation)
    parent = simulation.organisms[0]
    force_action(parent, Action.WAIT)

    tick_metrics = simulation.step()

    assert tick_metrics.births == 0
    assert parent.energy == 100.0
    assert simulation.metrics.total_births == 0


def test_exact_post_metabolism_threshold_reproduces(config_factory):
    simulation = Simulation.big_bang(
        config_factory(
            initial_organism_energy=91.0,
            initial_reproduction_threshold=90.0,
            base_energy_cost_per_tick=1.0,
        )
    )
    zero_world_energy(simulation)
    force_action(simulation.organisms[0], Action.WAIT)

    tick_metrics = simulation.step()

    assert tick_metrics.births == 1
    assert [
        organism.energy for organism in simulation.organisms
    ] == [45.0, 45.0]


def test_below_post_metabolism_threshold_does_not_reproduce(
    config_factory,
):
    simulation = Simulation.big_bang(
        config_factory(
            initial_organism_energy=90.0,
            initial_reproduction_threshold=90.0,
            base_energy_cost_per_tick=1.0,
        )
    )
    zero_world_energy(simulation)
    force_action(simulation.organisms[0], Action.WAIT)

    tick_metrics = simulation.step()

    assert tick_metrics.births == 0
    assert simulation.organisms[0].energy == 89.0


def test_one_by_one_world_has_no_birth_space(config_factory):
    simulation = Simulation.big_bang(
        config_factory(world_width=1, world_height=1)
    )
    zero_world_energy(simulation)
    parent = simulation.organisms[0]
    force_action(parent, Action.WAIT)

    tick_metrics = simulation.step()

    assert tick_metrics.births == 0
    assert tick_metrics.ending_population == 1
    assert parent.energy == 100.0


def test_newborn_position_is_reserved_immediately(config_factory):
    simulation = Simulation.big_bang(
        config_factory(
            world_width=3,
            world_height=3,
            initial_organisms=0,
        )
    )
    simulation.tick = 1

    first_parent = simulation._build_organism(
        genome=Genome(make_weights(), 90.0),
        energy=100.0,
        x=0,
        y=1,
        direction=Direction.NORTH,
        parent_id=None,
        birth_tick=0,
    )
    second_parent = simulation._build_organism(
        genome=Genome(make_weights(), 90.0),
        energy=100.0,
        x=2,
        y=1,
        direction=Direction.NORTH,
        parent_id=None,
        birth_tick=0,
    )
    occupied_positions = {
        (x, y)
        for x in range(3)
        for y in range(3)
        if (x, y) != (1, 1)
    }

    first_child = simulation._try_reproduce(
        first_parent,
        occupied_positions,
    )
    second_child = simulation._try_reproduce(
        second_parent,
        occupied_positions,
    )

    assert first_child is not None
    assert (first_child.x, first_child.y) == (1, 1)
    assert second_child is None
    assert second_parent.energy == 100.0
    assert simulation.metrics.total_births == 1


def test_reproduction_shuffles_a_copy_without_reordering_population(
    config_factory,
    monkeypatch,
):
    simulation = Simulation.big_bang(
        config_factory(initial_organisms=3, world_width=9)
    )
    zero_world_energy(simulation)
    for index, organism in enumerate(simulation.organisms):
        organism.x = index * 3
        organism.y = 2
        force_action(organism, Action.WAIT)

    population_order = [
        organism.organism_id for organism in simulation.organisms
    ]
    shuffle_inputs = []

    def reverse(items):
        shuffle_inputs.append(
            [organism.organism_id for organism in items]
        )
        items.reverse()

    monkeypatch.setattr(simulation.random, "shuffle", reverse)

    newborns = simulation._reproduce(simulation.organisms)

    assert shuffle_inputs == [population_order]
    assert [
        organism.organism_id for organism in simulation.organisms
    ] == population_order
    assert [child.parent_id for child in newborns] == [2, 1, 0]


def test_birth_and_death_accounting_are_independent(config_factory):
    simulation = Simulation.big_bang(
        config_factory(
            initial_organisms=2,
            initial_reproduction_threshold=100.0,
            base_energy_cost_per_tick=1.0,
        )
    )
    zero_world_energy(simulation)
    reproducing_parent, dying_organism = simulation.organisms
    reproducing_parent.energy = 200.0
    dying_organism.energy = 0.5
    force_action(reproducing_parent, Action.WAIT)
    force_action(dying_organism, Action.WAIT)

    tick_metrics = simulation.step()

    assert tick_metrics.starting_population == 2
    assert tick_metrics.deaths == 1
    assert tick_metrics.births == 1
    assert tick_metrics.ending_population == 2
    simulation._run_consistency_checks()


def test_zero_birth_report_uses_none(config_factory, capsys):
    simulation = Simulation.big_bang(
        config_factory(initial_reproduction_threshold=1_000.0)
    )
    zero_world_energy(simulation)
    force_action(simulation.organisms[0], Action.WAIT)
    simulation.step()

    simulation.print_experiment_report()
    report = capsys.readouterr().out

    assert "Total births                                 0" in report
    assert "First birth tick                             NONE" in report
    assert "Last birth tick                              NONE" in report
    assert "Parent ID(s) with most offspring             NONE" in report


def make_experiment_config(config_factory, seed: int):
    return config_factory(
        seed=seed,
        world_width=40,
        world_height=40,
        initial_organisms=100,
        initial_organism_energy=100.0,
        minimum_cell_energy=0,
        maximum_cell_energy=10,
        base_energy_cost_per_tick=1.0,
        wait_energy_cost=0.0,
        eat_energy_cost=0.25,
        turn_left_energy_cost=0.5,
        turn_right_energy_cost=0.5,
        move_forward_energy_cost=1.0,
        initial_reproduction_threshold=150.0,
        reproduction_energy_cost=0.0,
    )


def simulation_snapshot(simulation: Simulation):
    return (
        simulation.tick,
        simulation.metrics.total_births,
        simulation.metrics.first_birth_tick,
        simulation.metrics.last_birth_tick,
        simulation.metrics.peak_population,
        tuple(
            (
                organism.organism_id,
                organism.parent_id,
                organism.birth_tick,
                organism.x,
                organism.y,
                organism.direction,
                organism.energy,
            )
            for organism in simulation.organisms
        ),
        tuple(
            (
                tick.starting_population,
                tick.births,
                tick.deaths,
                tick.ending_population,
            )
            for tick in simulation.metrics.tick_history
        ),
    )


def test_seed_one_is_productive_and_replays_deterministically(
    config_factory,
):
    simulations = []
    for _ in range(2):
        simulation = Simulation.big_bang(
            make_experiment_config(config_factory, seed=1)
        )
        while simulation.tick < 60 and simulation.organisms:
            simulation.step()
        simulations.append(simulation)

    assert simulations[0].metrics.total_births > 0
    assert simulations[0].metrics.first_birth_tick == 43
    assert simulation_snapshot(simulations[0]) == simulation_snapshot(
        simulations[1]
    )


def test_seed_three_remains_zero_birth_control(config_factory):
    simulation = Simulation.big_bang(
        make_experiment_config(config_factory, seed=3)
    )
    while simulation.organisms and simulation.tick < 10_000:
        simulation.step()

    assert simulation.metrics.total_births == 0
    assert simulation.metrics.peak_population == 100
    assert simulation.tick == 207
    assert sum(simulation.metrics.action_counts.values()) == 7_773
    assert simulation.initial_world_energy - simulation.total_world_energy() == 435.0
    simulation._run_consistency_checks()
