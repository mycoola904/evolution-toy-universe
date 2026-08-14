# Evolution Toy Universe

Evolution Toy Universe is an experimental artificial life simulation that explores how complex behavior can emerge from a small set of simple rules.

Rather than attempting to model real biology, the project creates an artificial universe with its own consistent laws of physics. Organisms compete for energy, reproduce with mutation, and evolve over time. The goal is to observe the emergence of increasingly successful behaviors without hard-coding intelligence or strategy.

## Project Goals

- Build a deterministic simulation of an artificial world.
- Keep the initial design as simple as possible.
- Allow complexity to emerge naturally.
- Provide a platform for experimentation and visualization.

## Documentation

The project documentation is located in the `docs/` directory.

Suggested reading order:

1. Project Charter
2. Vision
3. Core Principles
4. Simulation Model
5. World Model
6. Organism Model
7. Energy Model
8. Reproduction
9. Neural System
10. User Interface
11. Technical Design
12. Roadmap
13. Architecture

## Current Status

The design phase is complete.

Development is now beginning on the Version 1 implementation.

## Running an Experiment

Run the simulation with the default seed (`4`):

```powershell
py src/main.py
```

Provide a different seed with `--seed`:

```powershell
py src/main.py --seed 123
```

Completed experiments are saved automatically to
`data/experiments.db`. Choose another SQLite database with `--database`:

```powershell
py src/main.py --seed 123 --database data/alternate-experiments.db
```

Run without creating or writing a database with `--no-persist`:

```powershell
py src/main.py --seed 123 --no-persist
```

Each saved run includes its complete configuration, termination reason, Git
commit and working-tree state when available, and one lifetime result for every
organism created during the experiment. SQLite write failures cause the command
to fail so an unsaved experiment is not reported as successfully recorded.

Each child's lifetime result also records its immediate parent and the number
of neural weights that actually changed at birth. A count of zero means the
child was born without a stored neural-weight difference; `NULL` identifies an
initial organism for which mutation-at-birth does not apply. For example:

```sql
SELECT
    organism_id AS child_organism_id,
    parent_organism_id,
    birth_tick,
    mutated_weight_count,
    CASE WHEN mutated_weight_count > 0 THEN 1 ELSE 0 END
        AS received_mutation
FROM organism_results
WHERE simulation_run_id = :simulation_run_id
  AND parent_organism_id IS NOT NULL
ORDER BY birth_tick, organism_id;
```

## License

See the LICENSE file for licensing information.
