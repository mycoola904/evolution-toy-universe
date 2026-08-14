# Mutation Observability Implementation Plan

## Goal

Persist one trustworthy mutation record for every successful birth so a saved
experiment can answer:

- which organism is the child's immediate parent;
- whether the child's inherited neural weights actually differ from the
  parent's weights;
- how many neural weights differ; and
- later, how large the genetic difference between child and parent is.

This branch should add observability without changing reproduction behavior,
mutation probabilities, random-number consumption, or deterministic results.

---

## Current State

The branch already provides most of the required lineage foundation:

- `Organism.parent_id` and `OrganismMetrics.parent_id` identify the immediate
  parent.
- `OrganismResult.parent_organism_id` carries that ID into the completed result.
- `organism_results.parent_organism_id` persists it as a run-local organism ID.
- Every organism's complete genome is persisted as JSON.
- `Genome.mutated_copy()` creates the child's weights but returns no metadata
  describing what changed.

The missing fact is the number of weights that actually changed at the birth.
Once that number is retained through metrics, result construction, and SQLite,
all three immediate questions are answerable.

Do not add a separate birth-events table for this phase. A successful birth
creates exactly one organism result, so another table would duplicate the
child ID, parent ID, and birth tick without adding a distinct lifecycle entity.

---

## Recommended Data Contract

Add one canonical field throughout the observability pipeline:

```python
mutated_weight_count: int | None
```

Use these meanings:

| Organism kind | `parent_organism_id` | `mutated_weight_count` |
| --- | ---: | ---: |
| Initial organism | `None` / SQL `NULL` | `None` / SQL `NULL` |
| Child with no changed weights | parent ID | `0` |
| Child with changed weights | parent ID | positive count |

Define "actually mutated" as:

```python
mutated_weight_count > 0
```

Count a weight only when the floating-point value stored in the child genome
differs from the corresponding value in the parent genome. This intentionally
does not count a mutation-rate roll that selects a weight but produces no
stored genetic change, including the valid configuration
`mutation_amount=0.0`.

Do not persist a second `did_mutate` Boolean. It is derived from the count and
would introduce an avoidable consistency risk. A result-model property or SQL
`CASE` expression may expose the friendlier Boolean name.

The complete record will remain distributed as follows:

| Question | Source of truth |
| --- | --- |
| Who is the child? | `organism_results.organism_id` |
| Who is its parent? | `organism_results.parent_organism_id` |
| When was it born? | `organism_results.birth_tick` |
| Did any neural weight change? | `mutated_weight_count > 0` |
| How many neural weights changed? | `mutated_weight_count` |
| What was inherited? | child and parent `genome` JSON |

---

## Event and Persistence Flow

```text
parent genome
    |
    v
Genome.mutated_copy()
    |
    +--> child genome
    |
    +--> compare parent and child weights at the birth boundary
             |
             v
       mutated_weight_count
             |
             v
OrganismMetrics -> OrganismResult -> organism_results
```

Capture the count immediately after mutation and before `_build_organism()`.
This makes it immutable event metadata even if genomes gain lifetime changes in
a future version.

---

## Phase 1: Add a Genome Comparison Primitive

In `src/domain/genome.py`, add a focused method such as:

```python
def neural_weight_difference_count(self, other: "Genome") -> int:
```

The method should iterate deterministically over every `Action` and `Sensor`
and count unequal stored weights. It must:

- make no random calls;
- mutate neither genome;
- validate or fail clearly if the two neural-weight topologies do not match;
- count only neural weights, not `reproduction_threshold`; and
- return a value from zero through `len(Action) * len(Sensor)`.

Keep `Genome.mutated_copy()` returning a `Genome`. Counting after the copy
preserves its existing API and makes the comparison operation reusable for
future lineage analysis.

At this stage, do not add an L1, L2, or percentage distance. First establish
the exact changed-weight count and its semantics.

---

## Phase 2: Capture Mutation Metadata at Birth

In `src/domain/simulation.py`:

1. Create the child genome in a local variable inside `_try_reproduce()`.
2. Compare it with `parent.genome` immediately.
3. Pass both the child genome and count into `_build_organism()`.
4. Pass `mutated_weight_count=None` when creating an initial organism.

Extend `_build_organism()` with:

```python
mutated_weight_count: int | None
```

Store the value only in `OrganismMetrics`, not `Organism`. Mutation metadata is
experimental history and has no role in sensing, decision-making, or other
organism behavior.

In `src/domain/simulation_metrics.py`, add the same field to
`OrganismMetrics` next to `parent_id` and `birth_tick`.

Extend `_run_consistency_checks()` so that:

- initial organisms have no parent and a `None` mutation count;
- every child has a known parent and a nonnegative integer count;
- no count exceeds the number of neural weights; and
- a child's stored count equals a fresh comparison with its parent's genome.

The last check is safe under the current model because neural networks do not
learn and genomes do not change during an organism's lifetime. The count
captured at birth remains the authoritative value for future models that may
relax that invariant.

---

## Phase 3: Carry the Field Through Completed Results

In `src/experiments/results.py`:

- add `mutated_weight_count: int | None` to `OrganismResult`;
- copy it from `OrganismMetrics` in `build_experiment_result()`; and
- optionally add a read-only convenience property:

```python
@property
def received_mutation(self) -> bool | None:
    if self.mutated_weight_count is None:
        return None
    return self.mutated_weight_count > 0
```

Returning `None` for an initial organism preserves the difference between
"not a birth" and "a birth with zero changed weights."

Do not recalculate the count while building the completed result. Result
construction should snapshot facts already observed by the simulation and
must remain free of random or behavioral work.

---

## Phase 4: Persist the Count in SQLite

In `src/persistence/database.py`, add this nullable column to
`organism_results`:

```sql
mutated_weight_count INTEGER
    CHECK (
        mutated_weight_count IS NULL
        OR mutated_weight_count >= 0
    ),
```

Add an index for child lookups:

```sql
CREATE INDEX IF NOT EXISTS idx_organism_results_parent
ON organism_results (simulation_run_id, parent_organism_id);
```

In `src/persistence/experiment_recorder.py`, include the new column in the
insert statement and bind `organism.mutated_weight_count`.

Keep `parent_organism_id` as a run-local ID. It identifies the parent only in
combination with `simulation_run_id`; it is not a globally unique organism ID.

### Existing database upgrade

`CREATE TABLE IF NOT EXISTS` does not modify an existing table. The default
`data/experiments.db` may therefore need an explicit, idempotent upgrade.

During `ExperimentDatabase.initialize()`:

1. Inspect `PRAGMA table_info(organism_results)`.
2. If the mutation-count column is absent, add it with `ALTER TABLE`.
3. Backfill existing child rows by joining each child to its parent within the
   same `simulation_run_id` and comparing their persisted `genome` JSON.
4. Leave initial-organism rows as `NULL`.
5. Create the parent index.
6. Record a schema version with `PRAGMA user_version` for subsequent changes.

Perform the upgrade in one transaction. If legacy JSON is malformed, a parent
is missing, or genome topology cannot be compared, fail with a clear migration
error and roll back instead of silently writing an incorrect count.

Backfilling is reliable under the current model: mutation occurs only when a
child is created, and genomes do not change later in life. It also preserves
the value of experiments already stored locally.

---

## Phase 5: Make the Saved Data Easy to Inspect

Document a query like this in `README.md` or the persistence documentation:

```sql
SELECT
    organism_id AS child_organism_id,
    parent_organism_id,
    birth_tick,
    mutated_weight_count,
    CASE WHEN mutated_weight_count > 0 THEN 1 ELSE 0 END
        AS received_mutation
FROM organism_results
WHERE simulation_run_id = ?
  AND parent_organism_id IS NOT NULL
ORDER BY birth_tick, organism_id;
```

Update `docs/10-technical-design.md` so the organism-result description lists
the per-birth mutation count and states that the Boolean answer is derived.

A new console-report section is not required for persistence correctness. It
can be added later if experiment-level mutation summaries become a regular
interactive need.

---

## Future Genetic-Distance Support

This phase already preserves the inputs needed for direct parent-child genetic
distance:

- the immediate parent ID;
- the child's complete genome JSON; and
- the parent's complete genome JSON.

The new count is the Hamming-style distance for neural weights: the number of
positions whose stored values differ. A later analysis layer can self-join
`organism_results` on run ID plus parent ID and calculate, without a schema
redesign:

- sum of absolute weight differences (L1 distance);
- Euclidean weight distance (L2 distance);
- maximum single-weight change;
- mean absolute change among changed weights; or
- normalized distance across the fixed neural topology.

Do not choose one of these as "genetic difference" in this branch. Each answers
a different scientific question. Also avoid storing derived distances until a
specific experiment requires one; they can be calculated from the persisted
genomes.

If genomes later become mutable during life, rename or replace the current
`genome` result with an explicit birth-genome snapshot before relying on it for
parent-child distance. The birth-time mutation count added here will remain
valid either way.

---

## Test Plan

### `tests/test_genome.py`

Add tests that verify:

1. identical genomes produce a count of zero;
2. exactly selected weight differences produce the exact count;
3. reproduction-threshold differences do not count as neural-weight changes;
4. comparison changes neither genome;
5. incompatible weight topology fails clearly; and
6. comparison consumes no random values.

### `tests/test_reproduction.py`

Add deterministic birth tests for:

1. `mutation_rate=0.0` produces a child count of zero;
2. `mutation_rate=1.0` with a positive amount changes every neural weight;
3. `mutation_rate=1.0` with `mutation_amount=0.0` records zero actual changes;
4. the initial organism's count is `None`;
5. the child's existing `parent_id` remains correct; and
6. recording the count does not change seeded child genomes or later random
   behavior.

### `tests/test_experiment_recorder.py`

Extend result factories and assertions to cover:

- `NULL` for an initial organism;
- `0` for an unmutated child;
- a positive value for a mutated child;
- the parent ID and mutation count surviving result construction together; and
- transaction rollback behavior remaining unchanged.

### `tests/test_database.py`

Verify:

1. fresh databases contain the new column and parent index;
2. repeated initialization remains idempotent;
3. negative counts are rejected;
4. a fixture using the legacy schema upgrades without losing run or organism
   rows;
5. legacy child rows are backfilled by comparing their genomes; and
6. `PRAGMA user_version` reports the expected schema version.

### Full verification

Run the complete test suite. Then run one seeded experiment with persistence
enabled and execute the inspection query above. Confirm that:

- the number of returned rows equals the run's number of births;
- every returned parent exists in the same run;
- zero and positive mutation counts both appear when the seed/configuration
  makes that expected; and
- rerunning the same seed and configuration produces identical mutation facts.

---

## Suggested Commit Sequence

1. **Add deterministic neural-weight difference counting**
2. **Capture per-birth mutation counts in simulation metrics**
3. **Persist mutation counts and upgrade existing experiment databases**
4. **Add lineage/mutation queries and update technical documentation**

Each commit should keep the full test suite passing and should not alter the
sequence of random calls.

---

## Out of Scope

- mutation of `reproduction_threshold` or other genome traits;
- storing one row per changed weight;
- classifying mutations as beneficial, neutral, or harmful;
- multi-generation ancestor tables or lineage closure tables;
- a single official genetic-distance formula;
- per-tick genome snapshots; and
- UI or graph visualization of lineage.

---

## Definition of Done

The branch is complete when a persisted run can answer, for every child:

> Which run-local organism is its parent, did at least one neural weight
> actually change at birth, and exactly how many neural weights changed?

Those answers must be deterministic, available for both new and upgraded
experiment databases, and backed by automated domain, result, migration, and
persistence tests. The stored parent and child genomes must remain sufficient
for a later analysis layer to calculate mutation magnitude without redesigning
the birth record.
