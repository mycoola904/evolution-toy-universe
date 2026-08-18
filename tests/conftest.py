import os

import pytest
from dotenv import load_dotenv

from domain.simulation_config import SimulationConfig
from persistence.database import (
    MIGRATIONS,
    PROJECT_ROOT,
    ExperimentDatabase,
    database_name_from_connection_info,
)


TEST_DATABASE_NAME = "evolution_toy_universe_test"


load_dotenv(PROJECT_ROOT / ".env", override=False)


@pytest.fixture(scope="session")
def test_database_url() -> str:
    connection_info = os.environ.get("TEST_DATABASE_URL")
    if connection_info is None or not connection_info.strip():
        pytest.fail(
            "TEST_DATABASE_URL must be set for PostgreSQL persistence tests"
        )

    configured_name = database_name_from_connection_info(connection_info)
    if configured_name != TEST_DATABASE_NAME:
        pytest.fail(
            "TEST_DATABASE_URL must name "
            f"{TEST_DATABASE_NAME!r}, not {configured_name!r}"
        )

    normal_connection_info = os.environ.get("DATABASE_URL")
    if normal_connection_info:
        normal_name = database_name_from_connection_info(
            normal_connection_info
        )
        if normal_name == TEST_DATABASE_NAME:
            pytest.fail(
                "DATABASE_URL must not point to the PostgreSQL test database"
            )

    database = ExperimentDatabase(connection_info)
    with database.connect() as connection:
        actual_name = connection.execute(
            "SELECT current_database()"
        ).fetchone()[0]
    if actual_name != TEST_DATABASE_NAME:
        pytest.fail(
            "TEST_DATABASE_URL connected to an unexpected database; "
            "test cleanup was refused"
        )

    return connection_info


def _restore_test_database(database: ExperimentDatabase) -> None:
    with database.connect() as connection:
        connection.execute(
            """
            TRUNCATE TABLE organism_results, simulation_runs
            RESTART IDENTITY CASCADE
            """
        )
        connection.execute("DELETE FROM schema_migrations")
        with connection.cursor() as cursor:
            cursor.executemany(
                """
                INSERT INTO schema_migrations (version, name, checksum)
                VALUES (%s, %s, %s)
                """,
                (
                    (migration.version, migration.name, migration.checksum)
                    for migration in MIGRATIONS
                ),
            )


@pytest.fixture
def database(test_database_url: str) -> ExperimentDatabase:
    database = ExperimentDatabase(test_database_url)
    database.initialize()
    _restore_test_database(database)

    yield database

    _restore_test_database(database)


@pytest.fixture
def config_factory():
    def build(**overrides) -> SimulationConfig:
        values = {
            "seed": 1,
            "world_width": 5,
            "world_height": 5,
            "initial_organisms": 1,
            "initial_organism_energy": 100.0,
            "minimum_cell_energy": 0,
            "maximum_cell_energy": 1,
            "regeneration_cell_count": 0,
            "regeneration_amount": 0.0,
            "minimum_initial_weight": -1.0,
            "maximum_initial_weight": 1.0,
            "base_energy_cost_per_tick": 0.0,
            "wait_energy_cost": 0.0,
            "eat_energy_cost": 0.0,
            "turn_left_energy_cost": 0.0,
            "turn_right_energy_cost": 0.0,
            "move_forward_energy_cost": 0.0,
            "initial_reproduction_threshold": 90.0,
            "reproduction_energy_cost": 0.0,
        }
        values.update(overrides)
        return SimulationConfig(**values)

    return build

