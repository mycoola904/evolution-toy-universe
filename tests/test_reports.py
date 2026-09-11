from datetime import datetime, timedelta, timezone

from psycopg.types.json import Jsonb

from persistence.reports import ExperimentReports


def insert_report_run(database, *, seed, started_at, ending_population=1):
    config = {
        "seed": seed,
        "max_ticks": 10,
        "world_width": 5,
        "world_height": 5,
        "initial_organisms": 1,
        "initial_organism_energy": 100.0,
        "regeneration_cell_count": 2,
        "regeneration_amount": 3.0,
        "initial_reproduction_threshold": 150.0,
        "mutation_rate": 0.01,
        "mutation_amount": 0.1,
    }
    with database.connect() as connection:
        run_id = connection.execute(
            """
            INSERT INTO simulation_runs (
                started_at, seed, world_width, world_height, ticks_completed,
                initial_organism_count, ending_organism_count,
                termination_reason, config_json
            ) VALUES (%s, %s, 5, 5, 10, 1, %s, 'tick_limit', %s)
            RETURNING id
            """,
            (started_at, seed, ending_population, Jsonb(config)),
        ).fetchone()[0]
        for organism_id, lifespan, peak, consumed, distance in (
            (0, 10, 120.0, 20.0, 4),
            (1, 4, 170.0, 40.0, 9),
        ):
            connection.execute(
                """
                INSERT INTO organism_results (
                    simulation_run_id, organism_id, birth_tick, lifespan,
                    initial_energy, final_energy, peak_energy,
                energy_consumed, distance_moved, genome
                ) VALUES (%s, %s, 0, %s, 100, 80, %s, %s, %s, %s)
                """,
                (
                    run_id,
                    organism_id,
                    lifespan,
                    peak,
                    consumed,
                    distance,
                    Jsonb({}),
                ),
            )
    return run_id


def test_run_detail_and_lifespan_distribution_are_aggregated(database):
    run_id = insert_report_run(
        database,
        seed=3,
        started_at=datetime(2026, 9, 10, tzinfo=timezone.utc),
    )
    reports = ExperimentReports(database)

    detail = reports.run_detail(run_id)
    distribution = reports.lifespan_distribution(run_id)

    assert detail is not None
    assert detail["total_organisms"] == 2
    assert detail["longest_lifespan"] == 10
    assert detail["average_lifespan"] == 7.0
    assert detail["highest_peak_energy"] == 170.0
    assert distribution == [
        {
            "lifespan": 4,
            "alive_at_end": True,
            "organism_count": 1,
            "percentage": 50.0,
        },
        {
            "lifespan": 10,
            "alive_at_end": True,
            "organism_count": 1,
            "percentage": 50.0,
        },
    ]


def test_recent_leaderboard_and_comparison_queries(database):
    now = datetime(2026, 9, 10, tzinfo=timezone.utc)
    first_id = insert_report_run(database, seed=1, started_at=now)
    second_id = insert_report_run(
        database,
        seed=2,
        started_at=now + timedelta(minutes=1),
        ending_population=2,
    )
    reports = ExperimentReports(database)

    assert [run["id"] for run in reports.recent_runs()] == [
        second_id,
        first_id,
    ]
    assert reports.leaderboard("peak_energy", 1)[0]["peak_energy"] == 170.0
    comparison = reports.compare_runs([first_id, second_id])
    assert [run["id"] for run in comparison] == [first_id, second_id]
    assert comparison[1]["total_organisms"] == 2


def test_organism_detail_loads_persisted_genome_and_relationships(database):
    run_id = insert_report_run(
        database,
        seed=8,
        started_at=datetime(2026, 9, 10, tzinfo=timezone.utc),
    )
    parent_genome = {
        "reproduction_threshold": 150.0,
        "weights": {"EAT": {"CELL_ENERGY": 0.97}},
    }
    child_genome = {
        "reproduction_threshold": 150.0,
        "weights": {"EAT": {"CELL_ENERGY": 1.04}},
    }
    with database.connect() as connection:
        connection.execute(
            "DELETE FROM organism_results WHERE simulation_run_id = %s",
            (run_id,),
        )
        with connection.cursor() as cursor:
            cursor.executemany(
                """
                INSERT INTO organism_results (
                    simulation_run_id, organism_id, parent_organism_id,
                    birth_tick, mutated_weight_count, death_tick, lifespan,
                    initial_energy, final_energy, peak_energy,
                    energy_consumed, distance_moved, genome
                ) VALUES (%s, %s, %s, %s, %s, NULL, 8, 100, 75, 120, 12, 2, %s)
                """,
                (
                    (run_id, 0, None, 0, None, Jsonb(parent_genome)),
                    (run_id, 1, 0, 2, 1, Jsonb(child_genome)),
                    (run_id, 2, 0, 3, 0, Jsonb(parent_genome)),
                ),
            )

    detail = ExperimentReports(database).organism_detail(run_id, 1)

    assert detail is not None
    assert detail.genome == child_genome
    assert detail.parent_organism_id == 0
    assert detail.sibling_organism_ids == (2,)
    assert detail.genome_comparison is not None
    assert detail.genome_comparison.changed_weights[0].path == "EAT.CELL_ENERGY"
    assert ExperimentReports(database).organism_detail(run_id, 999) is None


def test_organism_detail_loads_behavior_statistics(database):
    run_id = insert_report_run(
        database,
        seed=9,
        started_at=datetime(2026, 9, 10, tzinfo=timezone.utc),
    )
    with database.connect() as connection:
        connection.execute(
            """
            UPDATE organism_results
            SET wait_count = 2,
                eat_attempt_count = 2,
                successful_eat_count = 1,
                unsuccessful_eat_count = 1,
                move_forward_count = distance_moved,
                turn_left_count = 1,
                turn_right_count = lifespan - 2 - 2 - distance_moved - 1,
                final_action = 'TURN_RIGHT'
            WHERE simulation_run_id = %s AND organism_id = 0
            """,
            (run_id,),
        )

    detail = ExperimentReports(database).organism_detail(run_id, 0)

    assert detail is not None
    assert detail.behavior_available is True
    assert detail.total_actions == detail.lifespan
    assert detail.eat_success_rate == 50.0
    assert detail.final_action == "TURN_RIGHT"
