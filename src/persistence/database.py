from pathlib import Path
import sqlite3


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATABASE_PATH = PROJECT_ROOT / "data" / "experiments.db"


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
"""


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
            connection.executescript(SCHEMA)
