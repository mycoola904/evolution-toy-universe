import json
import sqlite3

import pytest

from persistence.database import (
    DatabaseMigrationError,
    ExperimentDatabase,
    SCHEMA_VERSION,
)


def test_initialize_creates_expected_schema(tmp_path):
    database = ExperimentDatabase(tmp_path / "nested" / "experiments.db")

    database.initialize()
    database.initialize()

    with database.connect() as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        run_columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(simulation_runs)"
            )
        }
        organism_columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(organism_results)"
            )
        }
        indexes = {
            row[1]
            for row in connection.execute(
                "PRAGMA index_list(organism_results)"
            )
        }
        schema_version = connection.execute(
            "PRAGMA user_version"
        ).fetchone()[0]

    assert {"simulation_runs", "organism_results"} <= tables
    assert {"termination_reason", "config_json", "git_dirty"} <= run_columns
    assert {
        "parent_organism_id",
        "mutated_weight_count",
        "initial_energy",
        "final_energy",
        "genome",
    } <= organism_columns
    assert "idx_organism_results_parent" in indexes
    assert schema_version == SCHEMA_VERSION


def test_every_connection_enforces_foreign_keys(tmp_path):
    database = ExperimentDatabase(tmp_path / "experiments.db")
    database.initialize()

    with pytest.raises(sqlite3.IntegrityError):
        with database.connect() as connection:
            connection.execute(
                """
                INSERT INTO organism_results (
                    simulation_run_id, organism_id, birth_tick, lifespan,
                    initial_energy, final_energy, peak_energy,
                    energy_consumed, distance_moved, genome
                ) VALUES (999, 0, 0, 1, 1, 0, 1, 0, 0, '{}')
                """
            )


def test_negative_mutation_count_is_rejected(tmp_path):
    database = ExperimentDatabase(tmp_path / "experiments.db")
    database.initialize()

    with database.connect() as connection:
        run_id = connection.execute(
            """
            INSERT INTO simulation_runs (
                started_at, seed, world_width, world_height,
                ticks_completed, initial_organism_count,
                ending_organism_count, termination_reason, config_json
            ) VALUES ('2026-08-14T00:00:00+00:00', 1, 1, 1, 1, 1, 1,
                      'tick_limit', '{}')
            """
        ).lastrowid

        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO organism_results (
                    simulation_run_id, organism_id, parent_organism_id,
                    birth_tick, mutated_weight_count, lifespan,
                    initial_energy, final_energy, peak_energy,
                    energy_consumed, distance_moved, genome
                ) VALUES (?, 1, 0, 1, -1, 0, 1, 1, 1, 0, 0, '{}')
                """,
                (run_id,),
            )


def test_initialize_upgrades_and_backfills_legacy_database(tmp_path):
    database_path = tmp_path / "legacy.db"
    parent_genome = {
        "reproduction_threshold": 90.0,
        "weights": {"WAIT": {"BIAS": 1.0, "CELL_ENERGY": 0.0}},
    }
    child_genome = {
        "reproduction_threshold": 90.0,
        "weights": {"WAIT": {"BIAS": 1.25, "CELL_ENERGY": 0.0}},
    }

    with sqlite3.connect(database_path) as connection:
        connection.executescript(
            """
            CREATE TABLE simulation_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                seed INTEGER NOT NULL,
                world_width INTEGER NOT NULL,
                world_height INTEGER NOT NULL,
                ticks_completed INTEGER NOT NULL,
                initial_organism_count INTEGER NOT NULL,
                ending_organism_count INTEGER NOT NULL,
                termination_reason TEXT NOT NULL,
                config_json TEXT NOT NULL,
                git_commit TEXT,
                git_dirty INTEGER
            );
            CREATE TABLE organism_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                simulation_run_id INTEGER NOT NULL,
                organism_id INTEGER NOT NULL,
                parent_organism_id INTEGER,
                birth_tick INTEGER NOT NULL,
                death_tick INTEGER,
                lifespan INTEGER NOT NULL,
                initial_energy REAL NOT NULL,
                final_energy REAL NOT NULL,
                peak_energy REAL NOT NULL,
                energy_consumed REAL NOT NULL,
                distance_moved INTEGER NOT NULL,
                genome TEXT NOT NULL,
                FOREIGN KEY (simulation_run_id) REFERENCES simulation_runs(id),
                UNIQUE (simulation_run_id, organism_id)
            );
            """
        )
        run_id = connection.execute(
            """
            INSERT INTO simulation_runs (
                started_at, seed, world_width, world_height,
                ticks_completed, initial_organism_count,
                ending_organism_count, termination_reason, config_json
            ) VALUES ('2026-08-14T00:00:00+00:00', 1, 2, 2, 1, 1, 2,
                      'tick_limit', '{}')
            """
        ).lastrowid
        connection.executemany(
            """
            INSERT INTO organism_results (
                simulation_run_id, organism_id, parent_organism_id,
                birth_tick, lifespan, initial_energy, final_energy,
                peak_energy, energy_consumed, distance_moved, genome
            ) VALUES (?, ?, ?, ?, 1, 50, 50, 50, 0, 0, ?)
            """,
            (
                (run_id, 0, None, 0, json.dumps(parent_genome)),
                (run_id, 1, 0, 1, json.dumps(child_genome)),
            ),
        )

    database = ExperimentDatabase(database_path)
    database.initialize()
    database.initialize()

    with database.connect() as connection:
        rows = connection.execute(
            """
            SELECT organism_id, mutated_weight_count
            FROM organism_results
            ORDER BY organism_id
            """
        ).fetchall()
        schema_version = connection.execute(
            "PRAGMA user_version"
        ).fetchone()[0]

    assert rows == [(0, None), (1, 1)]
    assert schema_version == SCHEMA_VERSION


def test_invalid_legacy_genome_rolls_back_backfill(tmp_path):
    database = ExperimentDatabase(tmp_path / "experiments.db")
    database.initialize()
    parent_genome = json.dumps(
        {"weights": {"WAIT": {"BIAS": 1.0}}}
    )

    with database.connect() as connection:
        run_id = connection.execute(
            """
            INSERT INTO simulation_runs (
                started_at, seed, world_width, world_height,
                ticks_completed, initial_organism_count,
                ending_organism_count, termination_reason, config_json
            ) VALUES ('2026-08-14T00:00:00+00:00', 1, 2, 2, 1, 1, 2,
                      'tick_limit', '{}')
            """
        ).lastrowid
        connection.executemany(
            """
            INSERT INTO organism_results (
                simulation_run_id, organism_id, parent_organism_id,
                birth_tick, mutated_weight_count, lifespan,
                initial_energy, final_energy, peak_energy,
                energy_consumed, distance_moved, genome
            ) VALUES (?, ?, ?, ?, NULL, 1, 50, 50, 50, 0, 0, ?)
            """,
            (
                (run_id, 0, None, 0, parent_genome),
                (run_id, 1, 0, 1, "not-json"),
            ),
        )

    with pytest.raises(DatabaseMigrationError, match="organism 1"):
        database.initialize()

    with database.connect() as connection:
        mutation_count = connection.execute(
            """
            SELECT mutated_weight_count
            FROM organism_results
            WHERE organism_id = 1
            """
        ).fetchone()[0]

    assert mutation_count is None
