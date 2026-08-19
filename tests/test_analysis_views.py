from datetime import datetime, timezone
from decimal import Decimal

import pytest
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from domain.action import Action
from domain.sensor import Sensor
from domain.simulation import Simulation
from experiments.results import build_experiment_result
from persistence.experiment_recorder import ExperimentRecorder


def insert_run(
    database,
    *,
    seed=43,
    ticks_completed=4,
    initial_organism_count=2,
    ending_organism_count=2,
    termination_reason="tick_limit",
    config=None,
    git_commit="abc123",
    git_dirty=False,
):
    if config is None:
        config = {}

    with database.connect() as connection:
        row = connection.execute(
            """
            INSERT INTO simulation_runs (
                started_at,
                seed,
                world_width,
                world_height,
                ticks_completed,
                initial_organism_count,
                ending_organism_count,
                termination_reason,
                config_json,
                git_commit,
                git_dirty
            ) VALUES (%s, %s, 5, 5, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                datetime(2026, 8, 18, 12, tzinfo=timezone.utc),
                seed,
                ticks_completed,
                initial_organism_count,
                ending_organism_count,
                termination_reason,
                Jsonb(config),
                git_commit,
                git_dirty,
            ),
        ).fetchone()

    assert row is not None
    return row[0]


def insert_organisms(database, run_id, organisms):
    values = []
    for organism in organisms:
        values.append(
            (
                run_id,
                organism["organism_id"],
                organism.get("parent_id"),
                organism.get("birth_tick", 0),
                organism.get("mutation_count"),
                organism.get("death_tick"),
                organism["lifespan"],
                organism.get("initial_energy", 100.0),
                organism.get("final_energy", 50.0),
                organism.get("peak_energy", 100.0),
                organism.get("energy_consumed", 0.0),
                organism.get("movement_count", 0),
                Jsonb(
                    organism.get(
                        "genome",
                        {
                            "reproduction_threshold": 100.0,
                            "weights": {},
                        },
                    )
                ),
            )
        )

    with database.connect() as connection:
        with connection.cursor() as cursor:
            cursor.executemany(
                """
                INSERT INTO organism_results (
                    simulation_run_id,
                    organism_id,
                    parent_organism_id,
                    birth_tick,
                    mutated_weight_count,
                    death_tick,
                    lifespan,
                    initial_energy,
                    final_energy,
                    peak_energy,
                    energy_consumed,
                    distance_moved,
                    genome
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s
                )
                """,
                values,
            )


def test_organism_and_reproduction_views(database):
    run_id = insert_run(database, seed=17)
    genome = {"reproduction_threshold": 91.0, "weights": {}}
    insert_organisms(
        database,
        run_id,
        [
            {
                "organism_id": 0,
                "death_tick": 3,
                "lifespan": 3,
                "final_energy": 0.0,
                "energy_consumed": 4.0,
            },
            {
                "organism_id": 1,
                "lifespan": 4,
                "final_energy": 75.0,
                "movement_count": 2,
            },
            {
                "organism_id": 2,
                "parent_id": 0,
                "birth_tick": 1,
                "mutation_count": 2,
                "death_tick": 4,
                "lifespan": 3,
                "initial_energy": 50.0,
                "final_energy": 0.0,
                "peak_energy": 80.0,
                "energy_consumed": 6.5,
                "movement_count": 3,
                "genome": genome,
            },
            {
                "organism_id": 3,
                "parent_id": 2,
                "birth_tick": 2,
                "mutation_count": 1,
                "lifespan": 2,
                "initial_energy": 40.0,
                "final_energy": 35.0,
            },
        ],
    )

    with database.connect() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            organism_rows = cursor.execute(
                """
                SELECT *
                FROM v_organism_outcomes
                WHERE run_id = %s
                ORDER BY organism_id
                """,
                (run_id,),
            ).fetchall()
            reproduction_rows = cursor.execute(
                """
                SELECT *
                FROM v_reproduction_outcomes
                WHERE run_id = %s
                ORDER BY organism_id
                """,
                (run_id,),
            ).fetchall()

    assert len(organism_rows) == 4
    assert organism_rows[2] == {
        "run_id": run_id,
        "seed": 17,
        "organism_id": 2,
        "parent_id": 0,
        "birth_tick": 1,
        "death_tick": 4,
        "lifespan": 3,
        "survived_to_end": False,
        "initial_energy": 50.0,
        "final_energy": 0.0,
        "peak_energy": 80.0,
        "energy_consumed": 6.5,
        "movement_count": 3,
        "mutation_count": 2,
        "genome": genome,
    }
    assert organism_rows[1]["survived_to_end"] is True

    assert [row["generation"] for row in reproduction_rows] == [0, 0, 1, 2]
    assert [row["offspring_count"] for row in reproduction_rows] == [1, 0, 1, 0]
    assert [row["reproduced"] for row in reproduction_rows] == [
        True,
        False,
        True,
        False,
    ]
    assert [row["survived_to_end"] for row in reproduction_rows] == [
        False,
        True,
        False,
        True,
    ]
    assert reproduction_rows[3]["parent_id"] == 2
    assert reproduction_rows[3]["mutation_count"] == 1


def test_reproduction_view_preserves_orphans_and_stops_cycles(database):
    run_id = insert_run(database, seed=18, initial_organism_count=1)
    insert_organisms(
        database,
        run_id,
        [
            {"organism_id": 0, "lifespan": 4},
            {
                "organism_id": 10,
                "parent_id": 999,
                "birth_tick": 1,
                "mutation_count": 0,
                "lifespan": 3,
            },
            {
                "organism_id": 20,
                "parent_id": 21,
                "birth_tick": 1,
                "mutation_count": 0,
                "lifespan": 3,
            },
            {
                "organism_id": 21,
                "parent_id": 20,
                "birth_tick": 2,
                "mutation_count": 0,
                "lifespan": 2,
            },
        ],
    )

    with database.connect() as connection:
        connection.execute("SET LOCAL statement_timeout = '2s'")
        rows = connection.execute(
            """
            SELECT organism_id, generation
            FROM v_reproduction_outcomes
            WHERE run_id = %s
            ORDER BY organism_id
            """,
            (run_id,),
        ).fetchall()

    assert rows == [(0, 0), (10, None), (20, None), (21, None)]


def test_experiment_view_derives_run_metrics_and_handles_config_history(
    database,
):
    valid_run_id = insert_run(
        database,
        config={
            "max_ticks": 5,
            "initial_reproduction_threshold": 90.0,
            "mutation_rate": 0.01,
            "mutation_amount": 0.1,
            "regeneration_cell_count": 3,
            "regeneration_amount": 2.5,
        },
    )
    insert_organisms(
        database,
        valid_run_id,
        [
            {
                "organism_id": 0,
                "death_tick": 2,
                "lifespan": 2,
                "energy_consumed": 1.0,
            },
            {
                "organism_id": 1,
                "lifespan": 4,
                "movement_count": 2,
            },
            {
                "organism_id": 2,
                "parent_id": 0,
                "birth_tick": 1,
                "mutation_count": 1,
                "death_tick": 3,
                "lifespan": 2,
                "energy_consumed": 2.5,
                "movement_count": 3,
            },
            {
                "organism_id": 3,
                "parent_id": 1,
                "birth_tick": 2,
                "mutation_count": 0,
                "lifespan": 2,
            },
        ],
    )
    missing_config_run_id = insert_run(database, seed=44, config={})
    malformed_config_run_id = insert_run(
        database,
        seed=45,
        config={
            "max_ticks": "10000",
            "initial_reproduction_threshold": {},
            "mutation_rate": True,
            "mutation_amount": None,
            "regeneration_cell_count": [],
            "regeneration_amount": "2.5",
        },
    )

    with database.connect() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            rows = cursor.execute(
                """
                SELECT *
                FROM v_experiment_runs
                ORDER BY run_id
                """
            ).fetchall()

    assert len(rows) == 3
    valid = rows[0]
    assert valid["run_id"] == valid_run_id
    assert valid["seed"] == 43
    assert valid["git_commit"] == "abc123"
    assert valid["git_dirty"] is False
    assert valid["termination_reason"] == "tick_limit"
    assert valid["final_tick"] == 4
    assert valid["max_ticks"] == Decimal("5")
    assert valid["reproduction_threshold"] == Decimal("90.0")
    assert valid["mutation_rate"] == Decimal("0.01")
    assert valid["mutation_magnitude"] == Decimal("0.1")
    assert valid["regeneration_cell_count"] == Decimal("3")
    assert valid["regeneration_amount"] == Decimal("2.5")
    assert valid["attempted_regeneration_per_tick"] == Decimal("7.5")
    assert valid["remaining_population"] == 2
    assert valid["total_organisms"] == 4
    assert valid["births"] == 2
    assert valid["deaths"] == 2
    assert valid["peak_population"] == Decimal("3")
    assert valid["total_world_energy_consumed"] == 3.5
    assert valid["total_moves"] == Decimal("5")
    assert valid["organisms_that_ate"] == 2
    assert valid["organisms_that_moved"] == 2

    missing = next(row for row in rows if row["run_id"] == missing_config_run_id)
    malformed = next(
        row for row in rows if row["run_id"] == malformed_config_run_id
    )
    config_columns = (
        "max_ticks",
        "reproduction_threshold",
        "mutation_rate",
        "mutation_magnitude",
        "regeneration_cell_count",
        "regeneration_amount",
        "attempted_regeneration_per_tick",
    )
    assert all(missing[column] is None for column in config_columns)
    assert all(malformed[column] is None for column in config_columns)


def zero_world_energy(simulation):
    for cell in simulation.world.cells:
        cell.energy = 0.0
    simulation.initial_world_energy = 0.0


def force_action(simulation, organism, selected_action):
    for action in Action:
        for sensor in Sensor:
            organism.genome.weights[action][sensor] = 0.0
    organism.genome.weights[selected_action][Sensor.BIAS] = 1.0


def persist_simulation(database, simulation):
    result = build_experiment_result(
        simulation=simulation,
        started_at=datetime(2026, 8, 18, 12, tzinfo=timezone.utc),
        git_commit=None,
        git_dirty=None,
    )
    run_id = ExperimentRecorder(database).save(result)
    total_actions = sum(simulation.metrics.action_counts.values())
    assert sum(organism.lifespan for organism in result.organisms) == (
        total_actions
    )
    return run_id


def test_peak_population_matches_simulation_tick_semantics(
    database,
    config_factory,
):
    no_births = Simulation.big_bang(
        config_factory(initial_reproduction_threshold=1_000.0)
    )
    zero_world_energy(no_births)
    force_action(no_births, no_births.organisms[0], Action.WAIT)
    no_births.step()

    births = Simulation.big_bang(
        config_factory(initial_reproduction_threshold=90.0)
    )
    zero_world_energy(births)
    force_action(births, births.organisms[0], Action.WAIT)
    births.step()

    deaths = Simulation.big_bang(
        config_factory(
            initial_organism_energy=1.0,
            initial_reproduction_threshold=1_000.0,
            base_energy_cost_per_tick=2.0,
        )
    )
    zero_world_energy(deaths)
    force_action(deaths, deaths.organisms[0], Action.WAIT)
    deaths.step()

    birth_and_death = Simulation.big_bang(
        config_factory(
            initial_organisms=2,
            initial_reproduction_threshold=100.0,
            base_energy_cost_per_tick=1.0,
        )
    )
    zero_world_energy(birth_and_death)
    reproducing_parent, dying_organism = birth_and_death.organisms
    reproducing_parent.energy = 200.0
    dying_organism.energy = 0.5
    force_action(birth_and_death, reproducing_parent, Action.WAIT)
    force_action(birth_and_death, dying_organism, Action.WAIT)
    tick = birth_and_death.step()
    assert tick.births == 1
    assert tick.deaths == 1

    simulations = [no_births, births, deaths, birth_and_death]
    expected = {
        persist_simulation(database, simulation): (
            simulation.metrics.peak_population
        )
        for simulation in simulations
    }

    with database.connect() as connection:
        rows = connection.execute(
            """
            SELECT run_id, peak_population
            FROM v_experiment_runs
            ORDER BY run_id
            """
        ).fetchall()

    assert {run_id: peak for run_id, peak in rows} == expected


@pytest.mark.parametrize(
    ("seed", "expected_final_tick", "expected_peak_population"),
    [
        (1, 171, 101),
        (3, 207, 100),
        (4, 161, 100),
    ],
)
def test_peak_population_matches_known_experiment_reports(
    database,
    config_factory,
    seed,
    expected_final_tick,
    expected_peak_population,
):
    simulation = Simulation.big_bang(
        config_factory(
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
    )
    while simulation.organisms and simulation.tick < 10_000:
        simulation.step()

    assert simulation.tick == expected_final_tick
    assert simulation.metrics.peak_population == expected_peak_population
    run_id = persist_simulation(database, simulation)

    with database.connect() as connection:
        peak_population = connection.execute(
            """
            SELECT peak_population
            FROM v_experiment_runs
            WHERE run_id = %s
            """,
            (run_id,),
        ).fetchone()[0]

    assert peak_population == expected_peak_population
