import sqlite3

import pytest

from persistence.database import ExperimentDatabase


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

    assert {"simulation_runs", "organism_results"} <= tables
    assert {"termination_reason", "config_json", "git_dirty"} <= run_columns
    assert {
        "parent_organism_id",
        "initial_energy",
        "final_energy",
        "genome",
    } <= organism_columns


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
