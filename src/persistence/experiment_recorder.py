import json

from experiments.results import ExperimentResult
from persistence.database import ExperimentDatabase


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
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    json.dumps(
                        run.config,
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                    run.git_commit,
                    (
                        None
                        if run.git_dirty is None
                        else int(run.git_dirty)
                    ),
                ),
            )
            run_id = cursor.lastrowid
            if run_id is None:
                raise RuntimeError("SQLite did not return a simulation run ID")

            connection.executemany(
                """
                INSERT INTO organism_results (
                    simulation_run_id,
                    organism_id,
                    parent_organism_id,
                    birth_tick,
                    death_tick,
                    lifespan,
                    initial_energy,
                    final_energy,
                    peak_energy,
                    energy_consumed,
                    distance_moved,
                    genome
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    (
                        run_id,
                        organism.organism_id,
                        organism.parent_organism_id,
                        organism.birth_tick,
                        organism.death_tick,
                        organism.lifespan,
                        organism.initial_energy,
                        organism.final_energy,
                        organism.peak_energy,
                        organism.energy_consumed,
                        organism.distance_moved,
                        json.dumps(
                            organism.genome,
                            sort_keys=True,
                            separators=(",", ":"),
                        ),
                    )
                    for organism in experiment_result.organisms
                ),
            )

        return run_id
