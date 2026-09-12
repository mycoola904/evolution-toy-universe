from typing import Any, Literal

from psycopg.rows import dict_row

from experiments.lineage import (
    FamilySummary,
    FamilyTreeNode,
    LineageAnalysis,
    analyze_lineages,
)
from experiments.lineage_mutations import (
    LineageMutationExplorer,
    build_lineage_mutation_explorer,
)
from experiments.organism_inspection import OrganismInspection, inspect_organism
from experiments.survivors import SurvivorExplorer, build_survivor_explorer
from persistence.database import ExperimentDatabase


LeaderboardMetric = Literal[
    "lifespan",
    "peak_energy",
    "energy_consumed",
    "distance_moved",
]

LEADERBOARD_COLUMNS: dict[LeaderboardMetric, str] = {
    "lifespan": "o.lifespan",
    "peak_energy": "o.peak_energy",
    "energy_consumed": "o.energy_consumed",
    "distance_moved": "o.distance_moved",
}


class ExperimentReports:
    """Read-only, parameterized reporting queries for completed experiments."""

    def __init__(self, database: ExperimentDatabase) -> None:
        self.database = database

    def recent_runs(self, limit: int = 25) -> list[dict[str, Any]]:
        with self.database.connect() as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                rows = cursor.execute(
                    """
                    SELECT
                        id,
                        started_at,
                        seed,
                        COALESCE((config_json ->> 'max_ticks')::BIGINT, 0)
                            AS max_ticks,
                        COALESCE(
                            (config_json ->> 'regeneration_amount')
                                ::DOUBLE PRECISION,
                            0
                        ) AS regeneration_amount,
                        initial_organism_count,
                        ending_organism_count,
                        ticks_completed,
                        termination_reason
                    FROM simulation_runs
                    ORDER BY started_at DESC, id DESC
                    LIMIT %s
                    """,
                    (limit,),
                ).fetchall()
        return rows

    def run_detail(self, run_id: int) -> dict[str, Any] | None:
        with self.database.connect() as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                return cursor.execute(
                    """
                    SELECT
                        r.id,
                        r.started_at,
                        r.seed,
                        r.world_width,
                        r.world_height,
                        r.ticks_completed,
                        r.initial_organism_count,
                        r.ending_organism_count,
                        r.termination_reason,
                        r.config_json,
                        r.report_json,
                        r.git_commit,
                        r.git_dirty,
                        COUNT(o.id)::INTEGER AS total_organisms,
                        COALESCE(MAX(o.lifespan), 0) AS longest_lifespan,
                        COALESCE(
                            AVG(o.lifespan)::DOUBLE PRECISION,
                            0
                        ) AS average_lifespan,
                        COALESCE(MAX(o.peak_energy), 0)
                            AS highest_peak_energy,
                        COALESCE(AVG(o.energy_consumed), 0)
                            AS average_energy_consumed,
                        COALESCE(
                            AVG(o.distance_moved)::DOUBLE PRECISION,
                            0
                        ) AS average_distance_moved
                    FROM simulation_runs AS r
                    LEFT JOIN organism_results AS o
                        ON o.simulation_run_id = r.id
                    WHERE r.id = %s
                    GROUP BY r.id
                    """,
                    (run_id,),
                ).fetchone()

    def lifespan_distribution(self, run_id: int) -> list[dict[str, Any]]:
        with self.database.connect() as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                rows = cursor.execute(
                    """
                    SELECT
                        lifespan,
                        death_tick IS NULL AS alive_at_end,
                        COUNT(*)::INTEGER AS organism_count
                    FROM organism_results
                    WHERE simulation_run_id = %s
                    GROUP BY lifespan, death_tick IS NULL
                    ORDER BY lifespan, alive_at_end
                    """,
                    (run_id,),
                ).fetchall()
        total = sum(row["organism_count"] for row in rows)
        return [
            {
                **row,
                "percentage": (
                    row["organism_count"] / total * 100.0 if total else 0.0
                ),
            }
            for row in rows
        ]

    def lineage_analysis(self, run_id: int) -> LineageAnalysis:
        with self.database.connect() as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                rows = cursor.execute(
                    """
                    SELECT
                        organism_id,
                        parent_organism_id,
                        birth_tick,
                        death_tick,
                        lifespan,
                        mutated_weight_count,
                        energy_consumed,
                        distance_moved
                    FROM organism_results
                    WHERE simulation_run_id = %s
                    ORDER BY organism_id
                    """,
                    (run_id,),
                ).fetchall()
        return analyze_lineages(rows)

    def family_summaries(self, run_id: int) -> tuple[FamilySummary, ...]:
        return self.lineage_analysis(run_id).families

    def survivor_explorer(self, run_id: int) -> SurvivorExplorer:
        with self.database.connect() as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                rows = cursor.execute(
                    """
                    SELECT
                        organism_id,
                        parent_organism_id,
                        birth_tick,
                        death_tick,
                        lifespan,
                        final_energy,
                        genome
                    FROM organism_results
                    WHERE simulation_run_id = %s
                    ORDER BY organism_id
                    """,
                    (run_id,),
                ).fetchall()
        return build_survivor_explorer(rows)

    def lineage_mutation_explorer(
        self,
        run_id: int,
        founder_id: int,
        genome_organism_id: int,
    ) -> LineageMutationExplorer | None:
        with self.database.connect() as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                rows = cursor.execute(
                    """
                    SELECT
                        organism_id,
                        parent_organism_id,
                        birth_tick,
                        death_tick,
                        mutated_weight_count,
                        genome
                    FROM organism_results
                    WHERE simulation_run_id = %s
                    ORDER BY organism_id
                    """,
                    (run_id,),
                ).fetchall()
        return build_lineage_mutation_explorer(
            rows,
            founder_organism_id=founder_id,
            selected_genome_organism_id=genome_organism_id,
        )

    def family_tree(
        self,
        run_id: int,
        founder_id: int,
    ) -> FamilyTreeNode | None:
        return self.lineage_analysis(run_id).trees_by_founder.get(founder_id)

    def organism_detail(
        self,
        run_id: int,
        organism_id: int,
    ) -> OrganismInspection | None:
        with self.database.connect() as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                rows = cursor.execute(
                    """
                    SELECT
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
                        wait_count,
                        eat_attempt_count,
                        successful_eat_count,
                        unsuccessful_eat_count,
                        move_forward_count,
                        turn_left_count,
                        turn_right_count,
                        final_action,
                        genome
                    FROM organism_results
                    WHERE simulation_run_id = %s
                    ORDER BY organism_id
                    """,
                    (run_id,),
                ).fetchall()
        return inspect_organism(rows, organism_id)

    def leaderboard(
        self,
        metric: LeaderboardMetric,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        column = LEADERBOARD_COLUMNS[metric]
        query = f"""
            SELECT
                o.simulation_run_id AS run_id,
                r.seed,
                o.organism_id,
                o.lifespan,
                o.peak_energy,
                o.energy_consumed,
                o.distance_moved
            FROM organism_results AS o
            JOIN simulation_runs AS r ON r.id = o.simulation_run_id
            ORDER BY {column} DESC, o.simulation_run_id DESC, o.organism_id
            LIMIT %s
        """
        with self.database.connect() as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                return cursor.execute(query, (limit,)).fetchall()

    def compare_runs(self, run_ids: list[int]) -> list[dict[str, Any]]:
        if len(set(run_ids)) < 2:
            raise ValueError("Select at least two different runs to compare")

        with self.database.connect() as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                return cursor.execute(
                    """
                    SELECT
                        r.id,
                        r.seed,
                        r.ticks_completed,
                        r.ending_organism_count,
                        r.config_json,
                        COUNT(o.id)::INTEGER AS total_organisms,
                        COALESCE(
                            AVG(o.lifespan)::DOUBLE PRECISION,
                            0
                        ) AS average_lifespan,
                        COALESCE(MAX(o.lifespan), 0) AS longest_lifespan,
                        COALESCE(AVG(o.energy_consumed), 0)
                            AS average_energy_consumed,
                        COALESCE(
                            AVG(o.distance_moved)::DOUBLE PRECISION,
                            0
                        ) AS average_distance_moved
                    FROM simulation_runs AS r
                    LEFT JOIN organism_results AS o
                        ON o.simulation_run_id = r.id
                    WHERE r.id = ANY(%s)
                    GROUP BY r.id
                    ORDER BY r.id
                    """,
                    (run_ids,),
                ).fetchall()
