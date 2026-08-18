from dataclasses import dataclass
from hashlib import sha256
from importlib import resources
from pathlib import Path
import re

import psycopg
from psycopg.conninfo import conninfo_to_dict


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MIGRATION_LOCK_ID = 4_552_841_101
MIGRATION_FILE_PATTERN = re.compile(
    r"^(?P<version>\d{3})_(?P<name>[a-z0-9_]+)\.sql$"
)

CREATE_MIGRATIONS_TABLE = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY
        CHECK (version > 0),
    name TEXT NOT NULL UNIQUE,
    checksum TEXT NOT NULL,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
)
"""


class DatabaseConfigurationError(ValueError):
    pass


class DatabaseMigrationError(RuntimeError):
    pass


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    checksum: str
    sql: str


def _load_migrations() -> tuple[Migration, ...]:
    migrations = []
    migration_root = resources.files("persistence.migrations")

    for resource in migration_root.iterdir():
        match = MIGRATION_FILE_PATTERN.fullmatch(resource.name)
        if match is None:
            continue

        sql = resource.read_text(encoding="utf-8")
        sql = sql.replace("\r\n", "\n").replace("\r", "\n")
        migrations.append(
            Migration(
                version=int(match.group("version")),
                name=match.group("name"),
                checksum=sha256(sql.encode("utf-8")).hexdigest(),
                sql=sql,
            )
        )

    migrations.sort(key=lambda migration: migration.version)
    versions = [migration.version for migration in migrations]
    expected_versions = list(range(1, len(migrations) + 1))
    if not migrations or versions != expected_versions:
        raise RuntimeError(
            "PostgreSQL migrations must be numbered consecutively from 001"
        )

    return tuple(migrations)


MIGRATIONS = _load_migrations()
SCHEMA_VERSION = MIGRATIONS[-1].version


def database_name_from_connection_info(connection_info: str) -> str:
    try:
        values = conninfo_to_dict(connection_info)
    except psycopg.Error as exc:
        raise DatabaseConfigurationError(
            "Invalid PostgreSQL connection information"
        ) from exc

    database_name = values.get("dbname")
    if not database_name:
        raise DatabaseConfigurationError(
            "PostgreSQL connection information must name a database"
        )
    return database_name


class ExperimentDatabase:
    def __init__(self, connection_info: str):
        if not connection_info or not connection_info.strip():
            raise DatabaseConfigurationError(
                "PostgreSQL connection information must not be empty"
            )

        self.connection_info = connection_info
        self.database_name = database_name_from_connection_info(
            connection_info
        )

    def connect(self) -> psycopg.Connection:
        return psycopg.connect(self.connection_info)

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.execute(
                "SELECT pg_advisory_xact_lock(%s)",
                (MIGRATION_LOCK_ID,),
            )
            connection.execute(CREATE_MIGRATIONS_TABLE)

            applied_rows = connection.execute(
                """
                SELECT version, name, checksum
                FROM schema_migrations
                ORDER BY version
                """
            ).fetchall()
            self._validate_applied_migrations(applied_rows)

            applied_versions = {row[0] for row in applied_rows}
            for migration in MIGRATIONS:
                if migration.version in applied_versions:
                    continue
                self._apply_migration(connection, migration)

    @staticmethod
    def _validate_applied_migrations(
        applied_rows: list[tuple[int, str, str]],
    ) -> None:
        known_by_version = {
            migration.version: migration for migration in MIGRATIONS
        }
        applied_versions = [row[0] for row in applied_rows]
        expected_prefix = [
            migration.version
            for migration in MIGRATIONS[: len(applied_rows)]
        ]

        if applied_versions != expected_prefix:
            unknown_versions = sorted(
                set(applied_versions) - set(known_by_version)
            )
            if unknown_versions:
                raise DatabaseMigrationError(
                    "database contains unsupported migration version(s): "
                    + ", ".join(map(str, unknown_versions))
                )
            raise DatabaseMigrationError(
                "database migration history is incomplete or out of order"
            )

        for version, name, checksum in applied_rows:
            known = known_by_version[version]
            if name != known.name or checksum != known.checksum:
                raise DatabaseMigrationError(
                    f"database migration {version:03d} does not match "
                    "the application migration"
                )

    @staticmethod
    def _apply_migration(
        connection: psycopg.Connection,
        migration: Migration,
    ) -> None:
        try:
            connection.execute(migration.sql)
            connection.execute(
                """
                INSERT INTO schema_migrations (
                    version,
                    name,
                    checksum
                ) VALUES (%s, %s, %s)
                """,
                (
                    migration.version,
                    migration.name,
                    migration.checksum,
                ),
            )
        except psycopg.Error as exc:
            raise DatabaseMigrationError(
                f"failed to apply PostgreSQL migration "
                f"{migration.version:03d}_{migration.name}"
            ) from exc
