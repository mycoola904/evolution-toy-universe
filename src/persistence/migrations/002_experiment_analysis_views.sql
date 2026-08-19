CREATE VIEW v_organism_outcomes AS
SELECT
    organism.simulation_run_id AS run_id,
    run.seed,
    organism.organism_id,
    organism.parent_organism_id AS parent_id,
    organism.birth_tick,
    organism.death_tick,
    organism.lifespan,
    organism.death_tick IS NULL AS survived_to_end,
    organism.initial_energy,
    organism.final_energy,
    organism.peak_energy,
    organism.energy_consumed,
    organism.distance_moved AS movement_count,
    organism.mutated_weight_count AS mutation_count,
    organism.genome
FROM organism_results AS organism
JOIN simulation_runs AS run
    ON run.id = organism.simulation_run_id;

CREATE VIEW v_reproduction_outcomes AS
WITH RECURSIVE lineage AS (
    SELECT
        organism.simulation_run_id,
        organism.organism_id,
        0 AS generation,
        ARRAY[organism.organism_id] AS path
    FROM organism_results AS organism
    WHERE organism.parent_organism_id IS NULL

    UNION ALL

    SELECT
        child.simulation_run_id,
        child.organism_id,
        parent.generation + 1,
        parent.path || child.organism_id
    FROM lineage AS parent
    JOIN organism_results AS child
        ON child.simulation_run_id = parent.simulation_run_id
        AND child.parent_organism_id = parent.organism_id
    WHERE NOT child.organism_id = ANY(parent.path)
),
offspring AS (
    SELECT
        simulation_run_id,
        parent_organism_id AS organism_id,
        COUNT(*) AS offspring_count
    FROM organism_results
    WHERE parent_organism_id IS NOT NULL
    GROUP BY simulation_run_id, parent_organism_id
)
SELECT
    organism.simulation_run_id AS run_id,
    run.seed,
    organism.organism_id,
    organism.parent_organism_id AS parent_id,
    lineage.generation,
    organism.birth_tick,
    organism.death_tick,
    organism.lifespan,
    organism.mutated_weight_count AS mutation_count,
    COALESCE(offspring.offspring_count, 0) AS offspring_count,
    COALESCE(offspring.offspring_count, 0) > 0 AS reproduced,
    organism.death_tick IS NULL AS survived_to_end
FROM organism_results AS organism
JOIN simulation_runs AS run
    ON run.id = organism.simulation_run_id
LEFT JOIN lineage
    ON lineage.simulation_run_id = organism.simulation_run_id
    AND lineage.organism_id = organism.organism_id
LEFT JOIN offspring
    ON offspring.simulation_run_id = organism.simulation_run_id
    AND offspring.organism_id = organism.organism_id;

CREATE VIEW v_experiment_runs AS
WITH resolved_runs AS (
    SELECT
        run.*,
        CASE
            WHEN jsonb_typeof(run.config_json -> 'max_ticks') = 'number'
            THEN (run.config_json ->> 'max_ticks')::NUMERIC
        END AS max_ticks,
        CASE
            WHEN jsonb_typeof(
                run.config_json -> 'initial_reproduction_threshold'
            ) = 'number'
            THEN (
                run.config_json ->> 'initial_reproduction_threshold'
            )::NUMERIC
        END AS reproduction_threshold,
        CASE
            WHEN jsonb_typeof(run.config_json -> 'mutation_rate') = 'number'
            THEN (run.config_json ->> 'mutation_rate')::NUMERIC
        END AS mutation_rate,
        CASE
            WHEN jsonb_typeof(
                run.config_json -> 'mutation_amount'
            ) = 'number'
            THEN (run.config_json ->> 'mutation_amount')::NUMERIC
        END AS mutation_magnitude,
        CASE
            WHEN jsonb_typeof(
                run.config_json -> 'regeneration_cell_count'
            ) = 'number'
            THEN (
                run.config_json ->> 'regeneration_cell_count'
            )::NUMERIC
        END AS regeneration_cell_count,
        CASE
            WHEN jsonb_typeof(
                run.config_json -> 'regeneration_amount'
            ) = 'number'
            THEN (run.config_json ->> 'regeneration_amount')::NUMERIC
        END AS regeneration_amount
    FROM simulation_runs AS run
),
organism_summary AS (
    SELECT
        simulation_run_id,
        COUNT(*) AS total_organisms,
        COUNT(*) FILTER (
            WHERE parent_organism_id IS NOT NULL
        ) AS births,
        COUNT(*) FILTER (
            WHERE death_tick IS NOT NULL
        ) AS deaths,
        COALESCE(SUM(energy_consumed), 0.0) AS total_world_energy_consumed,
        COALESCE(SUM(distance_moved), 0) AS total_moves,
        COUNT(*) FILTER (
            WHERE energy_consumed > 0.0
        ) AS organisms_that_ate,
        COUNT(*) FILTER (
            WHERE distance_moved > 0
        ) AS organisms_that_moved
    FROM organism_results
    GROUP BY simulation_run_id
),
population_events AS (
    SELECT
        simulation_run_id,
        birth_tick AS tick,
        COUNT(*) AS population_delta
    FROM organism_results
    GROUP BY simulation_run_id, birth_tick

    UNION ALL

    SELECT
        simulation_run_id,
        death_tick AS tick,
        -COUNT(*) AS population_delta
    FROM organism_results
    WHERE death_tick IS NOT NULL
    GROUP BY simulation_run_id, death_tick
),
population_deltas AS (
    SELECT
        simulation_run_id,
        tick,
        SUM(population_delta) AS population_delta
    FROM population_events
    GROUP BY simulation_run_id, tick
),
population_by_tick AS (
    SELECT
        simulation_run_id,
        tick,
        SUM(population_delta) OVER (
            PARTITION BY simulation_run_id
            ORDER BY tick
        ) AS population
    FROM population_deltas
),
peak_population AS (
    SELECT
        simulation_run_id,
        MAX(population) AS peak_population
    FROM population_by_tick
    GROUP BY simulation_run_id
)
SELECT
    run.id AS run_id,
    run.started_at,
    run.seed,
    run.git_commit,
    run.git_dirty,
    run.termination_reason,
    run.ticks_completed AS final_tick,
    run.world_width,
    run.world_height,
    run.initial_organism_count AS initial_population,
    run.max_ticks,
    run.reproduction_threshold,
    run.mutation_rate,
    run.mutation_magnitude,
    run.regeneration_cell_count,
    run.regeneration_amount,
    CASE
        WHEN run.regeneration_cell_count IS NOT NULL
            AND run.regeneration_amount IS NOT NULL
        THEN run.regeneration_cell_count * run.regeneration_amount
    END AS attempted_regeneration_per_tick,
    run.ending_organism_count AS remaining_population,
    COALESCE(summary.total_organisms, 0) AS total_organisms,
    COALESCE(summary.births, 0) AS births,
    COALESCE(summary.deaths, 0) AS deaths,
    COALESCE(
        peak.peak_population,
        run.initial_organism_count
    ) AS peak_population,
    COALESCE(
        summary.total_world_energy_consumed,
        0.0
    ) AS total_world_energy_consumed,
    COALESCE(summary.total_moves, 0) AS total_moves,
    COALESCE(summary.organisms_that_ate, 0) AS organisms_that_ate,
    COALESCE(summary.organisms_that_moved, 0) AS organisms_that_moved
FROM resolved_runs AS run
LEFT JOIN organism_summary AS summary
    ON summary.simulation_run_id = run.id
LEFT JOIN peak_population AS peak
    ON peak.simulation_run_id = run.id;
