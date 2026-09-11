from datetime import datetime, timezone
from hashlib import sha256

import psycopg
import pytest
from psycopg.types.json import Jsonb

import persistence.database as database_module
from persistence.database import (
    MIGRATIONS,
    SCHEMA_VERSION,
    DatabaseMigrationError,
    ExperimentDatabase,
    Migration,
)


def insert_run(database: ExperimentDatabase) -> int:
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
                config_json
            ) VALUES (%s, 1, 1, 1, 1, 1, 1, 'tick_limit', %s)
            RETURNING id
            """,
            (
                datetime(2026, 8, 14, tzinfo=timezone.utc),
                Jsonb({}),
            ),
        ).fetchone()

    assert row is not None
    return row[0]


def test_initialize_creates_expected_schema(
    database: ExperimentDatabase,
):
    database.initialize()
    database.initialize()

    with database.connect() as connection:
        tables = {
            row[0]
            for row in connection.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = current_schema()
                """
            )
        }
        run_columns = {
            row[0]
            for row in connection.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = current_schema()
                  AND table_name = 'simulation_runs'
                """
            )
        }
        organism_columns = {
            row[0]
            for row in connection.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = current_schema()
                  AND table_name = 'organism_results'
                """
            )
        }
        indexes = {
            row[0]
            for row in connection.execute(
                """
                SELECT indexname
                FROM pg_indexes
                WHERE schemaname = current_schema()
                  AND tablename = 'organism_results'
                """
            )
        }
        applied_migrations = connection.execute(
            """
            SELECT version, name, checksum
            FROM schema_migrations
            ORDER BY version
            """
        ).fetchall()

    assert {
        "schema_migrations",
        "simulation_runs",
        "organism_results",
    } <= tables
    assert {
        "termination_reason",
        "config_json",
        "report_json",
        "git_dirty",
    } <= run_columns
    assert {
        "parent_organism_id",
        "mutated_weight_count",
        "initial_energy",
        "final_energy",
        "genome",
        "wait_count",
        "eat_attempt_count",
        "successful_eat_count",
        "unsuccessful_eat_count",
        "move_forward_count",
        "turn_left_count",
        "turn_right_count",
        "final_action",
    } <= organism_columns
    assert "idx_organism_results_parent" in indexes
    assert applied_migrations == [
        (migration.version, migration.name, migration.checksum)
        for migration in MIGRATIONS
    ]
    assert applied_migrations[-1][0] == SCHEMA_VERSION


def test_every_connection_enforces_foreign_keys(
    database: ExperimentDatabase,
):
    with pytest.raises(psycopg.IntegrityError):
        with database.connect() as connection:
            connection.execute(
                """
                INSERT INTO organism_results (
                    simulation_run_id, organism_id, birth_tick, lifespan,
                    initial_energy, final_energy, peak_energy,
                    energy_consumed, distance_moved, genome
                ) VALUES (999, 0, 0, 1, 1, 0, 1, 0, 0, %s)
                """,
                (Jsonb({}),),
            )


def test_negative_mutation_count_is_rejected(
    database: ExperimentDatabase,
):
    run_id = insert_run(database)

    with pytest.raises(psycopg.IntegrityError):
        with database.connect() as connection:
            connection.execute(
                """
                INSERT INTO organism_results (
                    simulation_run_id, organism_id, parent_organism_id,
                    birth_tick, mutated_weight_count, lifespan,
                    initial_energy, final_energy, peak_energy,
                    energy_consumed, distance_moved, genome
                ) VALUES (%s, 1, 0, 1, -1, 0, 1, 1, 1, 0, 0, %s)
                """,
                (run_id, Jsonb({})),
            )


def test_legacy_organism_behavior_is_left_null(database: ExperimentDatabase):
    run_id = insert_run(database)
    with database.connect() as connection:
        connection.execute(
            """
            INSERT INTO organism_results (
                simulation_run_id, organism_id, birth_tick, lifespan,
                initial_energy, final_energy, peak_energy,
                energy_consumed, distance_moved, genome
            ) VALUES (%s, 0, 0, 1, 1, 1, 1, 0, 0, %s)
            """,
            (run_id, Jsonb({})),
        )
        stored = connection.execute(
            """
            SELECT wait_count, eat_attempt_count, successful_eat_count,
                   unsuccessful_eat_count, move_forward_count,
                   turn_left_count, turn_right_count, final_action
            FROM organism_results
            WHERE simulation_run_id = %s AND organism_id = 0
            """,
            (run_id,),
        ).fetchone()

    assert stored == (None,) * 8


@pytest.mark.parametrize(
    "behavior_values",
    (
        (1, 1, 1, 1, 0, 0, 0, "WAIT"),
        (-1, 1, 0, 1, 0, 0, 0, "WAIT"),
        (1, 1, 0, 1, 0, 0, 0, "FLY"),
    ),
)
def test_inconsistent_persisted_organism_behavior_is_rejected(
    database: ExperimentDatabase,
    behavior_values,
):
    run_id = insert_run(database)
    with pytest.raises(psycopg.IntegrityError):
        with database.connect() as connection:
            connection.execute(
                """
                INSERT INTO organism_results (
                    simulation_run_id, organism_id, birth_tick, lifespan,
                    initial_energy, final_energy, peak_energy,
                    energy_consumed, distance_moved, genome,
                    wait_count, eat_attempt_count, successful_eat_count,
                    unsuccessful_eat_count, move_forward_count,
                    turn_left_count, turn_right_count, final_action
                ) VALUES (%s, 0, 0, 1, 1, 1, 1, 0, 0, %s,
                          %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (run_id, Jsonb({}), *behavior_values),
            )


def test_initialize_rejects_unknown_newer_migration(
    database: ExperimentDatabase,
):
    with database.connect() as connection:
        connection.execute(
            """
            INSERT INTO schema_migrations (version, name, checksum)
            VALUES (999, 'future_schema', 'future-checksum')
            """
        )

    with pytest.raises(DatabaseMigrationError, match="unsupported.*999"):
        database.initialize()


def test_initialize_rejects_modified_applied_migration(
    database: ExperimentDatabase,
):
    with database.connect() as connection:
        connection.execute(
            """
            UPDATE schema_migrations
            SET checksum = 'modified-checksum'
            WHERE version = %s
            """,
            (SCHEMA_VERSION,),
        )

    with pytest.raises(DatabaseMigrationError, match="does not match"):
        database.initialize()


def test_failed_migration_rolls_back_schema_and_history(
    database: ExperimentDatabase,
    monkeypatch,
):
    failed_sql = """
    CREATE TABLE migration_rollback_probe (id INTEGER PRIMARY KEY);
    SELECT * FROM table_that_does_not_exist;
    """
    failed_migration = Migration(
        version=SCHEMA_VERSION + 1,
        name="intentional_failure",
        checksum=sha256(failed_sql.encode("utf-8")).hexdigest(),
        sql=failed_sql,
    )
    monkeypatch.setattr(
        database_module,
        "MIGRATIONS",
        (*MIGRATIONS, failed_migration),
    )

    with pytest.raises(DatabaseMigrationError, match="intentional_failure"):
        database.initialize()

    with database.connect() as connection:
        probe_table = connection.execute(
            "SELECT to_regclass('migration_rollback_probe')"
        ).fetchone()[0]
        migration_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM schema_migrations
            WHERE version = %s
            """,
            (failed_migration.version,),
        ).fetchone()[0]

    assert probe_table is None
    assert migration_count == 0
