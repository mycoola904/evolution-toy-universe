# Evolution Toy Universe — Experiment Persistence Implementation Plan

## Goal

Add Version 1 experiment persistence to **Evolution Toy Universe (TEU)** using Python's built-in `sqlite3` module and a local SQLite database.

The purpose of this feature is to preserve enough information about each simulation run that we can:

- identify the Git commit, working-tree state, seed, and configuration associated with a run;
- compare runs later;
- retain useful organism lifetime results;
- begin querying TEU as an experiment instead of relying on console output;
- support a future presentation layer, including a possible Django GUI, without making the simulation engine depend on Django or SQLite.

The persistence layer must remain separate from the simulation/domain logic.

---

# 1. Branch Scope

Suggested branch name:

```text
feature/experiment-persistence
```

This branch should implement only the first useful persistence layer.

## In Scope

Version 1 should persist:

### Experiment / simulation run

- run ID
- timestamp
- random seed
- world width
- world height
- ticks completed
- initial organism count
- ending organism count
- Git commit hash
- Git dirty flag
- termination reason
- the complete validated `SimulationConfig`, serialized as JSON

The individual seed and world-dimension columns remain useful for common SQL
queries. The complete configuration JSON is the authoritative record of all
Big Bang conditions, including energy costs, reproduction settings, and
initial weight bounds.

### Organism result

For each organism that exists during the run:

- organism identifier
- parent organism identifier, if applicable
- run ID
- birth tick
- death tick, if applicable
- lifespan
- initial energy
- final energy
- peak energy
- total energy consumed
- distance moved
- genome data

TEU already supports multiple organisms through reproduction. Persist organism
results through collections and loops so every organism that existed during
the run is recorded, including organisms that died before completion.

## Out of Scope

Do **not** add these yet:

- Django
- PostgreSQL
- SQLAlchemy or another ORM
- per-tick persistence
- neural-network activation history
- cell-by-cell history
- graphical reports
- automatic statistical analysis
- reproduction-specific genealogy tables
- run-summary tables containing values that can already be calculated with SQL
- database migrations framework

Keep Version 1 small and inspectable.

## Resolved Implementation Decisions

The following decisions are part of the Version 1 scope:

1. Every normal command-line run is persisted automatically.
2. `--database PATH` selects a database other than the default
   `data/experiments.db`.
3. `--no-persist` runs the simulation without creating or writing a database.
4. `started_at` records the run start in timezone-aware UTC ISO-8601 format and
   is captured immediately before `Simulation.big_bang()`.
5. Git commit and dirty state are best-effort provenance. If Git metadata is
   unavailable, both values are stored as `NULL`; unknown is not recorded as a
   clean working tree.
6. Git metadata failure does not prevent a simulation from running or being
   persisted.
7. SQLite initialization or write failure is fatal. The command must exit with
   an error rather than imply that an experiment was recorded successfully.
8. Organism IDs remain deterministic, run-local, and zero-based to match the
   current implementation.
9. Git provenance is captured at experiment start, before `Simulation.big_bang()`,
   so it describes the working tree associated with the experiment rather than
   the state after a long run finishes.
10. `final_energy` records the organism's domain value after normal simulation
    processing. The current death rule clamps a dead organism to `0.0`; a
    surviving organism retains its energy at the completed tick. Persistence
    does not independently clamp or rewrite either value.
11. The existing `SimulationMetrics.organism_metrics` collection is the
    deterministic archive of every organism created during the run, including
    organisms that died before completion. Add the missing energy snapshot
    fields there rather than introducing a second population model.

---

# 2. Architectural Principle

The simulation must not know how SQLite works.

Preferred dependency direction:

```text
Simulation / Domain
        |
        | produces state/results
        v
Persistence / Experiment Recorder
        |
        v
SQLite
```

Avoid:

```text
Simulation -> sqlite3 -> database
```

The `Simulation` class should continue to understand simulation concepts:

- ticks
- organisms
- cells
- energy
- movement
- neural decisions

It should **not** understand:

- SQL
- tables
- database connections
- INSERT statements
- database filenames

This separation will allow a future Django GUI to read the same experiment data without making Django part of the simulation engine.

---

# 3. Proposed Project Structure

The exact folder names can be adjusted to match the current repository, but a reasonable structure is:

```text
evolution-toy-universe/
|
|-- src/
|   |-- domain/
|   |   |-- cell.py
|   |   |-- direction.py
|   |   |-- genome.py
|   |   |-- neural_network.py
|   |   |-- organism.py
|   |   |-- simulation.py
|   |   `-- world.py
|   |
|   |-- experiments/
|   |   |-- __init__.py
|   |   `-- results.py
|   |
|   |-- persistence/
|   |   |-- __init__.py
|   |   |-- database.py
|   |   |-- experiment_recorder.py
|   |   `-- git_info.py
|   |
|   `-- main.py
|
|-- data/
|   `-- experiments.db
|
|-- tests/
|   |-- test_database.py
|   `-- test_experiment_recorder.py
```

The SQLite database file should normally **not** be committed to Git.

Add this to `.gitignore` if necessary:

```text
data/*.db
data/*.sqlite
data/*.sqlite3
```

Consider keeping the empty `data/` directory with:

```text
data/.gitkeep
```

---

# 4. Database Schema

Start with only two tables.

## Table: `simulation_runs`

Suggested fields:

```sql
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
);
```

Notes:

- `started_at` uses a timezone-aware UTC ISO-8601 timestamp captured immediately
  before `Simulation.big_bang()`.
- `config_json` contains every field of the validated `SimulationConfig`; use
  deterministic JSON serialization with sorted keys.
- SQLite does not have a dedicated Boolean storage class, so a known
  `git_dirty` value uses `0` or `1`.
- `git_commit` and `git_dirty` are nullable. Both are `NULL` when Git metadata
  cannot be obtained.
- `termination_reason` records why the run ended, initially `extinction` or
  `tick_limit`. If extinction occurs on the tick limit, use `extinction` to
  match the current report semantics.

---

## Table: `organism_results`

Suggested starting schema:

```sql
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
```

Enable SQLite foreign-key enforcement on every connection with
`PRAGMA foreign_keys = ON`.

`parent_organism_id` stores the already-known run-local parent ID for offspring
and is `NULL` for initial organisms. Version 1 does not add a separate genealogy
table; preserving this existing fact is sufficient for later lineage queries.

For Version 1, storing the genome as serialized text is acceptable.

JSON is a good candidate because it is:

- readable;
- easy to inspect;
- easy to reconstruct;
- easy to migrate later.

Do not over-design genome normalization yet.

---

# 5. Step-by-Step Implementation

## Step 1 — Create the Feature Branch

The repository is already on `feature/experiment-persistence`. Confirm the
branch and preserve the existing documentation relocation under `docs/plans/`:

```bash
git status
```

Do not create another branch or discard the existing documentation changes.
The working tree may remain dirty while the feature is being developed; the
clean/dirty provenance test occurs after the intended changes are committed.

### Suggested commit

No commit is necessary just for creating the branch.

---

# 6. Step 2 — Create the Persistence Package

Create:

```text
src/persistence/
    __init__.py
    database.py
```

The first responsibility of `database.py` should be very small:

1. know where the SQLite file lives;
2. create a connection;
3. create required tables if they do not exist.

Conceptually:

```python
class ExperimentDatabase:
    def __init__(self, db_path):
        self.db_path = db_path

    def initialize(self):
        ...

    def connect(self):
        ...
```

Do not add simulation-specific behavior yet.

## Test

Write a small automated test that:

1. creates a temporary SQLite file;
2. calls database initialization;
3. verifies that `simulation_runs` exists;
4. verifies that `organism_results` exists.

Use a temporary database during tests rather than the real `data/experiments.db`.

### Stop Point

At this point:

- no simulation behavior has changed;
- the database can be created;
- the schema can be verified independently.

### Suggested commit

```text
Add SQLite experiment database initialization
```

---

# 7. Step 3 — Capture Git Metadata

Create:

```text
src/persistence/git_info.py
```

Its responsibility should be to answer two questions:

```text
What commit am I running?
Is the working tree dirty?
```

Suggested interface:

```python
@dataclass
class GitInfo:
    commit_hash: str | None
    dirty: bool | None
```

and:

```python
def get_git_info() -> GitInfo:
    ...
```

Possible Git commands:

```bash
git rev-parse HEAD
git status --porcelain
```

The persistence layer should handle failure gracefully.

For example, if TEU is copied outside a Git repository:

```text
commit_hash = None
dirty = None
```

The simulation should not fail merely because Git information is unavailable.
The database should store both Git fields as `NULL` in this case. This keeps an
unknown working-tree state distinct from a verified clean tree.

## Test

Test Git parsing independently where practical.

At minimum verify manually that:

```python
print(get_git_info())
```

returns the current commit and correct dirty state.

Then modify a harmless tracked file temporarily and confirm dirty becomes `True`.

Undo the temporary edit afterward.

### Suggested commit

```text
Add Git provenance capture for experiments
```

---

# 8. Step 4 — Verify Existing Simulation Instrumentation

Persistence can only save information that the simulation actually knows.

The current simulation already tracks stable zero-based organism IDs, birth
and death ticks, peak energy, energy consumed from cells, movement actions,
parent IDs, and offspring counts. Steps 5 through 9 should verify and reuse
that instrumentation rather than duplicate it.

Add only the missing persistence facts:

- initial energy;
- current/final energy;
- deterministic genome serialization.

The current `SimulationMetrics.organism_metrics` dictionary already retains one
record for every organism created, including dead organisms, and its insertion
order follows deterministic organism-ID allocation. Extend `OrganismMetrics`
with `initial_energy` and `final_energy`; do not add `dead_organisms` or
`all_organisms` collections solely for persistence.

For Version 1, `distance_moved` is the organism's existing `MOVE_FORWARD`
action count because movement in the current toroidal world always succeeds.

Define the energy snapshots consistently:

- an initial organism's initial energy is its energy at creation;
- a child's initial energy is its energy immediately after the reproduction
  split;
- a dead organism's final energy is `0.0`, matching the domain's current death
  handling;
- a surviving organism's final energy is its energy at the completed tick;
- update final-energy metrics after every energy-changing phase, including
  reproduction splits, and after the domain applies its death clamp.

Important distinction:

These are **simulation facts**, not persistence facts.

Therefore they belong in the domain model if they describe the organism itself.

SQLite IDs, SQL rows, database paths, and INSERT logic do **not** belong in the organism.

---

# 9. Step 5 — Verify Stable Organism IDs

Confirm that the current simulation assigns deterministic, run-local,
zero-based organism IDs and that offspring continue the same sequence.

Avoid using Python's memory identity:

```python
id(organism)
```

That is not stable or meaningful between runs.

The current convention should remain:

```text
0
1
2
3
...
```

Do not introduce a second persistence-specific organism ID.

## Test

Verify that:

1. the initial organism receives the expected zero-based ID;
2. offspring receive deterministic subsequent IDs;
3. rerunning the same deterministic scenario produces the same organism ID
   sequence.

### Suggested commit

Only commit code here if inspection reveals missing or incorrect behavior.
Do not add duplicate ID machinery solely for persistence.

---

# 10. Step 6 — Verify Peak Energy Tracking

Confirm that the current domain logic maintains:

```text
peak_energy = max(previous_peak_energy, current_energy)
```

and that peak energy begins at the organism's initial energy.

Do not move this calculation into the database layer.

## Test

Construct or run a case where energy rises above the initial value and verify
that the existing peak-energy value reflects the highest observed value.

If the current implementation already passes this test, no production-code
change is required.

---

# 11. Step 7 — Verify Energy Consumed Tracking

For Version 1:

> `energy_consumed` means energy acquired by the organism from environmental
> food/energy sources.

Confirm that the current implementation accumulates the **actual** energy
transferred from the cell, not merely the amount requested.

Example:

```text
cell energy = 3
organism attempts to eat 5
actual energy consumed = 3
```

Therefore:

```text
energy_consumed += 3
```

## Test

Use a known cell energy value and confirm the existing accumulator matches the
actual energy transfer.

If the current implementation already behaves this way, reuse it unchanged.

---

# 12. Step 8 — Verify Distance Moved

For the current grid simulation, Version 1 defines:

> One successful `MOVE_FORWARD` action equals one unit of distance.

Confirm that the existing movement-action count provides this value. Do not
calculate Euclidean distance between start and finish; an organism that wanders
and returns to its starting point should still have moved.

## Test

Move an organism a known number of times and verify the existing counter.

If the current implementation already tracks successful movement actions
correctly, no new domain field is required.

---

# 13. Step 9 — Verify Birth, Death, Lifespan, and Complete Metrics Retention

Confirm the current conventions for:

- `birth_tick`;
- `death_tick`;
- lifespan;
- parent organism ID;
- retention of one metrics record for every organism created.

For the initial organism:

```text
birth_tick = 0
```

If an organism dies:

```text
death_tick = current_tick
```

Use one explicit lifespan definition everywhere:

```text
lifespan = number of simulation ticks the organism remained alive
```

Be careful about off-by-one behavior.

For an organism still alive when the run ends:

```text
death_tick = NULL
lifespan = current_tick - birth_tick
```

Use `simulation.metrics.organism_metrics`, sorted by `organism_id`, as the
complete source for result snapshot creation. Dead organisms are removed from
`simulation.organisms`, but their metrics records remain available. Extend
those records with initial and final energy rather than retaining dead mutable
`Organism` instances.

## Test

Verify that:

1. a dead organism's metrics remain available for result snapshot creation;
2. a surviving organism's metrics are also available;
3. the result set contains every organism created during the run exactly once;
4. result snapshots are ordered deterministically by organism ID;
5. `parent_id`, lifespan, initial energy, and final energy are correct for both
   initial organisms and offspring.

---

# 14. Step 10 — Serialize the Genome

The recorder needs a stable, readable representation of the genome.

Prefer adding a method to `Genome` such as:

```python
def to_dict(self) -> dict:
    ...
```

Then persistence can serialize it:

```python
json.dumps(genome.to_dict())
```

This is preferable to saving:

```python
str(genome)
```

or:

```python
repr(genome)
```

because those representations may change and may not contain all data.

## Test

Verify:

```python
genome_data = genome.to_dict()
```

contains every value necessary to reproduce or inspect the genome.

If practical, also verify the JSON can be read back successfully.

### Suggested commit

```text
Add organism metrics and genome serialization
```

---

# 15. Step 11 — Introduce Experiment Result Data Objects

Before SQL insertion, create plain data structures representing what will be saved.

Place these in the neutral `src/experiments/results.py` module so the domain
does not depend on SQLite and the recorder receives completed snapshots rather
than reaching through live simulation objects.

Example:

```python
@dataclass(frozen=True)
class SimulationRunResult:
    started_at: str
    seed: int
    world_width: int
    world_height: int
    ticks_completed: int
    initial_organism_count: int
    ending_organism_count: int
    termination_reason: str
    config: dict
    git_commit: str | None
    git_dirty: bool | None
```

and:

```python
@dataclass(frozen=True)
class OrganismResult:
    organism_id: int
    parent_organism_id: int | None
    birth_tick: int
    death_tick: int | None
    lifespan: int
    initial_energy: float
    final_energy: float
    peak_energy: float
    energy_consumed: float
    distance_moved: int
    genome: dict
```

Wrap the completed run and organism snapshots in one small aggregate:

```python
@dataclass(frozen=True)
class ExperimentResult:
    run: SimulationRunResult
    organisms: tuple[OrganismResult, ...]
```

This makes the recorder contract explicit: one experiment consists of exactly
one run snapshot plus the complete organism-result collection.

The important idea is:

```text
simulation state -> ExperimentResult -> persistence
```

rather than:

```text
database reaches into every simulation object
```

Keep these result objects simple.

They are snapshots of what happened.

Capture `started_at` and Git provenance immediately before
`Simulation.big_bang()` using a timezone-aware UTC timestamp for `started_at`.
Build organism snapshots in deterministic organism-ID order after the run
completes from `SimulationMetrics.organism_metrics`. Snapshot creation must
neither consume random values nor mutate simulation state.

---

# 16. Step 12 — Build the Experiment Recorder

Create:

```text
src/persistence/experiment_recorder.py
```

Suggested responsibility:

```python
class ExperimentRecorder:
    def __init__(self, database):
        self.database = database

    def save(self, experiment_result):
        ...
```

The recorder should:

1. open a database transaction;
2. insert one `simulation_runs` row;
3. obtain its generated run ID;
4. insert all associated `organism_results`;
5. commit the transaction.

If anything fails during the operation, the transaction should roll back so that the database does not contain half of an experiment.

Return the generated run ID after a successful commit. A database
initialization or write error is fatal and should propagate to the command-line
entry point so the process exits with an error. Do not print a success message
unless the transaction commits.

Conceptual flow:

```text
BEGIN
  INSERT simulation run
  get run ID

  FOR each organism result
      INSERT organism result

COMMIT
```

This is where the complete organism-result collection is persisted.

Use:

```python
for organism_result in organism_results:
    ...
```

so the recorder handles the reproduced population uniformly and does not
depend on population size.

## Test

Using a temporary database:

1. save one fake run;
2. save one fake organism result;
3. query the database;
4. verify every stored value, including the complete configuration JSON;
5. verify `termination_reason`;
6. verify `parent_organism_id` for offspring and `NULL` for initial organisms;
7. save multiple organism results and verify their associations;
8. force an organism insert failure and verify the complete run rolls back.

### Suggested commit

```text
Add experiment recorder
```

---

# 17. Step 13 — Integrate Persistence at the Application Boundary

Only after the database and recorder work independently should persistence be added to the running application.

The integration should occur near the outer application layer, in
`src/main.py`, rather than deep inside `Simulation.step()`.

Conceptually:

```python
config = create_config(...)

started_at = None
git_info = None
if not options.no_persist:
    started_at = datetime.now(timezone.utc)
    git_info = get_git_info()

simulation = Simulation.big_bang(config)
simulation.run(...)

if not options.no_persist:
    experiment_result = build_experiment_result(
        simulation=simulation,
        started_at=started_at,
        git_info=git_info,
    )

    database = ExperimentDatabase(options.database)
    database.initialize()

    recorder = ExperimentRecorder(database)
    run_id = recorder.save(experiment_result)
```

Add these command-line options:

```text
--database PATH   SQLite database path (default: data/experiments.db)
--no-persist      Run without creating or writing a database
```

Every normal command-line run persists automatically. `--no-persist` takes
precedence over `--database`; when it is present, no database directory or file
should be created and Git provenance need not be collected. Resolve the default
database path from the repository root so it does not change with the caller's
working directory. The exact helper names may vary, but persistence remains in
`src/main.py` or another outer application module.

The key rule:

> Finishing a simulation may trigger persistence, but simulation mechanics should not contain SQL.

---

# 18. Step 14 — Decide When a Run Is Considered Complete

Use the current command-line experiment end condition: run until the population
is extinct or the 10,000-tick limit is reached.

Persistence should happen after that run finishes.

Persist the reason explicitly:

```text
extinction
tick_limit
```

Do not require later analysis code to infer the termination reason from tick
count and ending population. If the final tick also causes extinction,
`extinction` takes precedence, matching the current report.

Later we can support:

- manual stop;
- maximum tick limit;
- extinction;
- experiment configuration rules.

Version 1 only needs the current run behavior. Both extinction and tick-limit
completion are persisted; interrupted or crashed runs are not persisted.

---

# 19. Step 15 — First Real Persistence Test

Use a known seed such as the seed already used in development.

Run TEU once.

Then inspect SQLite directly.

If the SQLite command-line client is installed, inspect it with:

```bash
sqlite3 data/experiments.db
```

On Windows, Python includes SQLite support but does not necessarily install the
`sqlite3` command-line executable. If the CLI is unavailable, inspect the same
database with Python's `sqlite3` module, a VS Code SQLite extension, or another
SQLite database viewer.

Inside SQLite:

```sql
.tables
```

Then:

```sql
SELECT *
FROM simulation_runs;
```

And:

```sql
SELECT *
FROM organism_results;
```

Verify manually:

- seed is correct;
- ticks are correct;
- world dimensions are correct;
- termination reason is correct;
- Git hash matches `git rev-parse HEAD`;
- dirty flag is correct;
- organism metrics agree with console/debug observations;
- parent organism IDs are preserved;
- dead organisms are present in the results;
- genome JSON looks readable.

Exit with:

```text
.quit
```

---

# 20. Step 16 — Test Git Dirty Behavior

This is an important provenance test.

## Clean run

Commit all changes.

Run TEU.

Expected:

```text
git_dirty = 0
```

## Dirty run

Make a harmless change to a tracked source file but do not commit it.

Run TEU again.

Expected:

```text
git_dirty = 1
```

Undo or commit the temporary change afterward.

Then query:

```sql
SELECT
    id,
    seed,
    git_commit,
    git_dirty
FROM simulation_runs
ORDER BY id;
```

The database should preserve the distinction between the two experiments.

---

# 21. Step 17 — Add Useful Verification Queries

Keep a few SQL queries in documentation or a development notes file.

## Recent runs

```sql
SELECT
    id,
    started_at,
    seed,
    ticks_completed,
    git_commit,
    git_dirty
FROM simulation_runs
ORDER BY id DESC
LIMIT 10;
```

## Longest-lived organisms

```sql
SELECT
    simulation_run_id,
    organism_id,
    lifespan
FROM organism_results
ORDER BY lifespan DESC
LIMIT 10;
```

## Most energy consumed

```sql
SELECT
    simulation_run_id,
    organism_id,
    energy_consumed
FROM organism_results
ORDER BY energy_consumed DESC
LIMIT 10;
```

## Most mobile organisms

```sql
SELECT
    simulation_run_id,
    organism_id,
    distance_moved
FROM organism_results
ORDER BY distance_moved DESC
LIMIT 10;
```

## Highest peak energy

```sql
SELECT
    simulation_run_id,
    organism_id,
    peak_energy
FROM organism_results
ORDER BY peak_energy DESC
LIMIT 10;
```

These queries demonstrate why a separate run-summary table is unnecessary for Version 1.

---

# 22. Step 18 — Automated End-to-End Test

Add one integration test that exercises the entire feature:

1. create a temporary database;
2. create a deterministic simulation with a known seed;
3. run a small number of ticks;
4. collect results;
5. persist the experiment;
6. query the database;
7. verify the run row, including termination reason;
8. verify all organism rows, including organisms that died before completion;
9. verify parent organism IDs where offspring exist.

This becomes the safety net for future refactoring.

It will become especially valuable as TEU gains:

- larger populations;
- richer reproduction and lineage behavior;
- additional mutation behavior;
- more actions;
- more complex energy rules.

### Suggested commit

```text
Add experiment persistence integration tests
```

---

# 23. Step 19 — Update Documentation

Update the technical/design documentation with a short persistence section.

Document these decisions:

1. SQLite is the Version 1 experiment database.
2. Persistence is outside the domain model.
3. The simulation engine does not depend on Django or SQLite.
4. Runs store Git commit and dirty-state provenance.
5. Organism lifetime summaries are persisted.
6. Existing parent organism IDs are preserved without adding a separate
   genealogy table.
7. Run termination reason is persisted explicitly.
8. Per-tick history is intentionally not persisted in Version 1.
9. Derived leaderboards are calculated with queries rather than duplicated into summary tables.

Also document the database location:

```text
data/experiments.db
```

### Suggested commit

```text
Document experiment persistence architecture
```

---

# 24. Step 20 — Final Branch Review

Before merging, verify:

- [ ] All tests pass.
- [ ] Existing simulation behavior still works.
- [ ] The database is not committed.
- [ ] `data/*.db` is ignored.
- [ ] A fresh checkout can create the database automatically.
- [ ] A clean run records `git_dirty = 0`.
- [ ] A modified working tree records `git_dirty = 1`.
- [ ] A run without available Git metadata records both Git fields as `NULL`.
- [ ] Seed is persisted correctly.
- [ ] World dimensions are persisted correctly.
- [ ] Every validated `SimulationConfig` field is present in `config_json`.
- [ ] Tick count is persisted correctly.
- [ ] Termination reason is persisted correctly.
- [ ] Organism results are persisted.
- [ ] Every organism created during the run is persisted exactly once,
      including organisms that died before completion.
- [ ] Parent organism IDs are persisted for offspring and `NULL` for initial
      organisms.
- [ ] Dead-organism `final_energy` is `0.0` after the domain's death handling,
      while surviving-organism `final_energy` matches its completed-tick value.
- [ ] Genome data is readable.
- [ ] Normal CLI runs persist automatically to `data/experiments.db`.
- [ ] `--database PATH` writes to the selected database.
- [ ] `--no-persist` creates no database directory or file.
- [ ] Database initialization and write failures produce a failing command.
- [ ] SQL is absent from the domain classes.
- [ ] Persistence code does not affect random-number generation.
- [ ] Re-running with the same seed does not receive random values from persistence code.
- [ ] Every organism that existed during the run is inserted through a loop.
- [ ] Documentation reflects the implemented design.

---

# 25. Suggested Commit Sequence

A clean history might look like:

```text
Add SQLite experiment database initialization

Add Git provenance capture for experiments

Track organism lifetime metrics for persistence

Add organism genome serialization

Add experiment result models

Add experiment recorder

Integrate experiment persistence with simulation runs

Add experiment persistence integration tests

Document experiment persistence architecture
```

Do not force this exact commit structure if a step turns out to be too small or tightly coupled to another one.

The goal is understandable commits, not maximum commit count.

---

# 26. Important Design Guardrails

## Guardrail 1 — Persistence must not consume RNG values

The persistence feature must never call the simulation's random-number generator.

Otherwise simply enabling persistence could change a seeded simulation.

This is a critical reproducibility rule.

---

## Guardrail 2 — Do not persist every tick yet

A per-tick history table would create significant complexity and data volume before we know what questions we actually need it to answer.

Start with lifetime summaries.

Add detailed history only after experiments demonstrate a need for it.

---

## Guardrail 3 — Do not make the organism know about its database row

Avoid fields like:

```python
organism.database_id
```

unless a future design gives us a compelling reason.

The organism should have a simulation identity:

```text
organism_id
```

not a SQLite identity.

---

## Guardrail 4 — Do not make SQLite the source of live simulation state

The active universe should remain in memory.

SQLite records the experiment.

It does not drive each simulation tick.

Preferred:

```text
Memory = live universe
SQLite = historical experiment record
```

---

## Guardrail 5 — Preserve reproducibility

A stored run should let us say:

```text
This result came from:

seed       = 42
commit     = abc123...
dirty      = false
world      = 20 x 20
```

For a clean working tree, the Git commit plus configuration provides strong
reproducibility. For a dirty working tree, the database records that the run
contained uncommitted changes, but Version 1 does not attempt to preserve the
Git diff. A dirty run therefore has useful provenance without claiming exact
source reconstruction.

As experiment configuration grows, new configuration values should also be persisted.

The database should gradually become a record of the complete Big Bang conditions.

---

# 27. Future Extensions — Not Part of This Branch

Once Version 1 works, the architecture should support future additions without redesigning everything.

Possible later additions:

## Experiment configuration

- initial organism count
- initial energy range
- cell energy rules
- mutation rate
- action costs
- neural-network configuration

## Reproduction Persistence and Lineage Analysis

- generation number
- mutation details
- richer lineage queries
- optional dedicated genealogy structures if later analysis requires them

## Run termination

- extinction
- tick limit
- manual stop
- other experiment-defined condition

## Analysis

- average lifespan by genome characteristic
- survival distributions
- energy efficiency
- mobility vs survival
- reproduction success
- mutation success

## Presentation

A future Django application could use the experiment database to show:

- run history;
- organism leaderboards;
- genome inspection;
- run comparisons;
- charts;
- experiment configuration;
- lineage trees.

The simulation engine should remain independent of Django.

---

# 28. Recommended Working Order for Our Sessions

Rather than implementing the entire branch at once, work through these milestones one at a time:

### Milestone A — Database foundation

- confirm the existing `feature/experiment-persistence` branch;
- preserve the documentation relocation already in the working tree;
- add `src/persistence/`;
- initialize SQLite;
- create tables;
- test schema.

### Milestone B — Reproducibility metadata

- capture Git commit;
- capture dirty state;
- use `NULL` for unavailable Git metadata;
- test clean, dirty, and unavailable states.

### Milestone C — Organism measurements

- stable organism ID;
- initial/final/peak energy;
- energy consumed;
- distance moved;
- birth/death/lifespan;
- complete metrics retention for dead and surviving organisms;
- parent organism IDs;
- final-energy snapshot semantics;
- genome serialization.

### Milestone D — Result snapshots

- create simulation/run result objects;
- create organism result objects;
- wrap them in `ExperimentResult`;
- snapshot the complete validated configuration;
- include termination reason and parent organism IDs;
- verify them before involving SQL.

### Milestone E — Recorder

- insert run;
- insert organism results in a loop;
- transaction handling;
- recorder tests.

### Milestone F — Application integration

- invoke recorder at the application boundary;
- add automatic persistence, `--database`, and `--no-persist`;
- treat database failures as fatal;
- perform a real seeded run;
- inspect SQLite manually.

### Milestone G — Finish

- integration test;
- documentation;
- final branch review;
- merge.

---

# Definition of Done

The experiment persistence branch is complete when TEU can run a deterministic simulation and produce a SQLite record that tells us:

> **What universe did we start with, what source provenance and configuration
> were associated with it, why did the run end, and what happened to every
> organism?**

At that point TEU will have moved from a transient simulation program to the beginning of an experimental system.
