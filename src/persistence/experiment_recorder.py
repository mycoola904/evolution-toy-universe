from experiments.results import ExperimentResult
from persistence.database import ExperimentDatabase
from psycopg.types.json import Jsonb


class ExperimentRecorder:
    def __init__(self, database: ExperimentDatabase):
        self.database = database

    def save(self, experiment_result: ExperimentResult) -> int:
        run = experiment_result.run

        with self.database.connect() as connection:
            cursor = connection.execute(
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
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    run.started_at,
                    run.seed,
                    run.world_width,
                    run.world_height,
                    run.ticks_completed,
                    run.initial_organism_count,
                    run.ending_organism_count,
                    run.termination_reason,
                    Jsonb(run.config),
                    run.git_commit,
                    run.git_dirty,
                ),
            )
            row = cursor.fetchone()
            if row is None:
                raise RuntimeError(
                    "PostgreSQL did not return a simulation run ID"
                )
            run_id = row[0]

            with connection.cursor() as organism_cursor:
                organism_cursor.executemany(
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
                    (
                        (
                            run_id,
                            organism.organism_id,
                            organism.parent_organism_id,
                            organism.birth_tick,
                            organism.mutated_weight_count,
                            organism.death_tick,
                            organism.lifespan,
                            organism.initial_energy,
                            organism.final_energy,
                            organism.peak_energy,
                            organism.energy_consumed,
                            organism.distance_moved,
                            Jsonb(organism.genome),
                        )
                        for organism in experiment_result.organisms
                    ),
                )

        return run_id
