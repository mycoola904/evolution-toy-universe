import json
from pathlib import Path
import sqlite3


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATABASE_PATH = PROJECT_ROOT / "data" / "experiments.db"
SCHEMA_VERSION = 2


SCHEMA = """
CREATE TABLE IF NOT EXISTS simulation_runs (
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
        CHECK (git_dirty IN (0, 1) OR git_dirty IS NULL)
);

CREATE TABLE IF NOT EXISTS organism_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    simulation_run_id INTEGER NOT NULL,
    organism_id INTEGER NOT NULL,
    parent_organism_id INTEGER,
    birth_tick INTEGER NOT NULL,
    mutated_weight_count INTEGER
        CHECK (
            mutated_weight_count IS NULL
            OR mutated_weight_count >= 0
        ),
    death_tick INTEGER,
    lifespan INTEGER NOT NULL,
    initial_energy REAL NOT NULL,
    final_energy REAL NOT NULL,
    peak_energy REAL NOT NULL,
    energy_consumed REAL NOT NULL,
    distance_moved INTEGER NOT NULL,
    genome TEXT NOT NULL,

    FOREIGN KEY (simulation_run_id)
        REFERENCES simulation_runs(id),
    UNIQUE (simulation_run_id, organism_id)
);

CREATE INDEX IF NOT EXISTS idx_organism_results_parent
ON organism_results (simulation_run_id, parent_organism_id);
"""


class DatabaseMigrationError(RuntimeError):
    pass


class ExperimentDatabase:
    def __init__(self, db_path: str | Path = DEFAULT_DATABASE_PATH):
        self.db_path = Path(db_path)

    def connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.db_path)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize(self) -> None:
        with self.connect() as connection:
            current_version = connection.execute(
                "PRAGMA user_version"
            ).fetchone()[0]
            if current_version > SCHEMA_VERSION:
                raise DatabaseMigrationError(
                    "database schema version "
                    f"{current_version} is newer than supported version "
                    f"{SCHEMA_VERSION}"
                )

            connection.executescript("BEGIN;\n" + SCHEMA)
            self._add_mutation_count_column_if_missing(connection)
            self._backfill_mutation_counts(connection)
            connection.execute(
                f"PRAGMA user_version = {SCHEMA_VERSION}"
            )

    def _add_mutation_count_column_if_missing(
        self,
        connection: sqlite3.Connection,
    ) -> None:
        columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(organism_results)"
            )
        }
        if "mutated_weight_count" in columns:
            return

        connection.execute(
            """
            ALTER TABLE organism_results
            ADD COLUMN mutated_weight_count INTEGER
                CHECK (
                    mutated_weight_count IS NULL
                    OR mutated_weight_count >= 0
                )
            """
        )

    def _backfill_mutation_counts(
        self,
        connection: sqlite3.Connection,
    ) -> None:
        legacy_children = connection.execute(
            """
            SELECT
                child.id,
                child.simulation_run_id,
                child.organism_id,
                child.genome,
                parent.genome
            FROM organism_results AS child
            LEFT JOIN organism_results AS parent
                ON parent.simulation_run_id = child.simulation_run_id
                AND parent.organism_id = child.parent_organism_id
            WHERE child.parent_organism_id IS NOT NULL
              AND child.mutated_weight_count IS NULL
            """
        ).fetchall()

        for (
            row_id,
            simulation_run_id,
            organism_id,
            child_genome_json,
            parent_genome_json,
        ) in legacy_children:
            if parent_genome_json is None:
                raise DatabaseMigrationError(
                    "cannot backfill mutation count for organism "
                    f"{organism_id} in simulation run {simulation_run_id}: "
                    "parent organism is missing"
                )

            try:
                count = self._neural_weight_difference_count(
                    child_genome_json,
                    parent_genome_json,
                )
            except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
                raise DatabaseMigrationError(
                    "cannot backfill mutation count for organism "
                    f"{organism_id} in simulation run {simulation_run_id}: "
                    "invalid or incompatible genome JSON"
                ) from exc

            connection.execute(
                """
                UPDATE organism_results
                SET mutated_weight_count = ?
                WHERE id = ?
                """,
                (count, row_id),
            )

    @staticmethod
    def _neural_weight_difference_count(
        child_genome_json: str,
        parent_genome_json: str,
    ) -> int:
        child_weights = json.loads(child_genome_json)["weights"]
        parent_weights = json.loads(parent_genome_json)["weights"]

        if (
            not isinstance(child_weights, dict)
            or not isinstance(parent_weights, dict)
            or set(child_weights) != set(parent_weights)
        ):
            raise ValueError("genome actions do not match")

        difference_count = 0
        for action, child_sensor_weights in child_weights.items():
            parent_sensor_weights = parent_weights[action]
            if (
                not isinstance(child_sensor_weights, dict)
                or not isinstance(parent_sensor_weights, dict)
                or set(child_sensor_weights) != set(parent_sensor_weights)
            ):
                raise ValueError("genome sensors do not match")

            difference_count += sum(
                child_weight != parent_sensor_weights[sensor]
                for sensor, child_weight in child_sensor_weights.items()
            )

        return difference_count
