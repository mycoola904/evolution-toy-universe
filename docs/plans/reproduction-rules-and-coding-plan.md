# Reproduction Phase 1: Rules and Coding Plan

## Purpose

This branch implements the first experimental reproduction milestone for the
Toy Universe. It adds automatic asexual reproduction, energy division, genome
inheritance, immediate-parent lineage, and reproduction observability.

This is **Reproduction Phase 1**, not the final reproduction design.

## Scope

Reproduction Phase 1 includes:

- automatic reproduction based on stored energy;
- placement of offspring in an available orthogonal neighboring position;
- equal division of reproduction energy;
- exact genome copying without mutation;
- permanent organism IDs and immediate-parent lineage;
- birth, population, and offspring metrics;
- deterministic experiments and automated tests.

The following work is explicitly deferred:

- mutation;
- final simultaneous birth-placement conflict resolution;
- global collision and occupancy enforcement;
- changes to initial placement or movement collision behavior;
- environmental energy renewal;
- new sensors;
- changed neural behavior;
- changed movement rules.

### Occupancy Scope Statement

Reproduction Phase 1 prevents newborns from being placed in positions occupied
at the start of the reproductive phase or reserved by an earlier successful
birth. Existing organism overlap caused by initialization or movement is outside
this branch's scope. Consequently, this implementation does not yet satisfy the
global one-organism-per-cell invariant documented by the World Model.

Tests for this branch must verify reproduction-phase occupancy without asserting
that the entire simulation already enforces exclusive occupancy.

## Reproduction Rules

| Question | Phase 1 decision |
|---|---|
| **When does reproduction occur?** | Automatically when post-action, post-metabolism energy is at or above the organism's reproduction threshold and is sufficient to pay the reproduction cost. |
| **Initial reproduction threshold?** | **150.0**. Initial organisms start at 100.0, so they must prosper before reproducing. |
| **Where is the threshold stored?** | In the **Genome**. `SimulationConfig` supplies the initial Big Bang value. |
| **Is reproduction an Action?** | **No.** It is a lifecycle event after the normal action, metabolism, and death processing for the tick. |
| **Who may reproduce?** | Only organisms that survive the tick's action and energy costs. |
| **How many births per parent per tick?** | Maximum **one**. |
| **Where does the child appear?** | Randomly in one available orthogonal neighboring position, with world wrapping. |
| **How are wrapped neighbors represented?** | Return unique positions in deterministic north, east, south, west discovery order. This matters in narrow worlds where multiple directions can wrap to the same position. |
| **What if every neighboring position is occupied?** | No reproduction that tick. The parent keeps its energy and may try again next tick. |
| **How is provisional parent priority determined?** | Shuffle eligible parents using the simulation-owned RNG, then process that shuffled copy sequentially. Never reorder the living population list. |
| **How are successful positions protected?** | Reserve each newborn position immediately so another birth in the same phase cannot use it. |
| **Energy division?** | After the reproduction cost, split the remaining energy **50/50** between parent and child. |
| **Reproduction cost?** | Configurable, with an initial value of **0.0**. The threshold and cost must be finite and nonnegative. |
| **What if energy cannot pay the cost?** | Reproduction does not occur and the parent keeps its energy. |
| **Child genome?** | A true deep copy of the parent's genome. Mutation is deferred to a later reproduction phase. |
| **Child direction?** | Inherit the parent's direction. |
| **Does the child act immediately?** | **No.** It joins the population after the reproductive phase and first acts on the next tick. |
| **Can the child reproduce on its birth tick?** | **No.** Newborns are not part of the current tick's eligible-parent collection. |
| **Can the parent reproduce again later?** | Yes, whenever it again satisfies the energy and space requirements. |
| **Lineage?** | The child receives a new permanent organism ID and `parent_id=parent.organism_id`. Initial organisms have `parent_id=None`. |
| **Birth ticks?** | Initial organisms use `birth_tick=0`. A child born during tick N uses `birth_tick=N`. |

## Provisional Birth-Placement Policy

Final simultaneous conflict resolution is deferred. Phase 1 uses a reproducible,
random-priority approximation:

1. Build the eligible-parent list without consuming random values.
2. Copy that list.
3. Shuffle the copy once using the simulation-owned RNG.
4. Process parents in that shuffled order.
5. For each parent, choose randomly from positions that are still available.
6. Reserve a successful position immediately.
7. Leave blocked parents and their energy unchanged.

This avoids permanent priority based on organism ID or insertion order while
remaining deterministic for a known seed. It is still sequential: later parents
see reservations made by earlier parents. That limitation is accepted for this
experimental phase and must not be presented as the final conflict model.

Shuffling must not occur when there are no eligible parents. Avoiding unnecessary
random calls preserves reproduction-free behavior until an organism actually
becomes eligible.

## Coding Plan

### Step 1: Keep the Branch Focused

Use the existing branch:

```text
feature/reproduction
```

Do not add deferred mutation, collision resolution, environmental renewal,
sensors, neural changes, or movement changes to this branch.

### Step 2: Introduce Pytest

Add `pytest` as the project's test dependency and create a `tests/` directory.
Tests must be runnable from the repository root with:

```text
pytest
```

### Step 3: Add and Validate Reproduction Configuration

Add to `SimulationConfig`:

```python
initial_reproduction_threshold: float = 150.0
reproduction_energy_cost: float = 0.0
```

Validate that both values are finite and nonnegative. A reproduction attempt
also requires:

```python
parent.energy >= parent.genome.reproduction_threshold
parent.energy >= config.reproduction_energy_cost
```

If either condition fails, reproduction does not occur and no reproduction
energy is charged.

### Step 4: Extend the Genome

Add the reproduction threshold to `Genome`:

```python
class Genome:
    def __init__(
        self,
        weights: dict[Action, dict[Sensor, float]],
        reproduction_threshold: float,
    ):
        self.weights = weights
        self.reproduction_threshold = reproduction_threshold
```

Update `Genome.random_genome()` to receive the initial threshold from
configuration. The threshold is not randomized in Phase 1.

### Step 5: Add a True Genome Copy Method

Add:

```python
def copy(self) -> "Genome":
```

The method must copy the reproduction threshold and create a new nested weights
structure. Parent and child must have:

```text
equal genome values
different Genome objects
different outer weights dictionaries
different nested sensor-weight dictionaries
```

### Step 6: Add Lineage to Organism

Add:

```python
parent_id: int | None = None
```

Initial organisms use `parent_id=None`. Offspring use the parent's permanent ID.

### Step 7: Refactor Common Organism Construction

Extract common construction into a helper such as:

```python
def _build_organism(
    self,
    genome: Genome,
    energy: float,
    x: int,
    y: int,
    direction: Direction,
    parent_id: int | None,
    birth_tick: int,
) -> Organism:
```

The helper must:

1. Allocate the next permanent organism ID.
2. Build a `NeuralNetwork` from the supplied genome.
3. Construct the organism.
4. Register its `OrganismMetrics`.
5. Return the organism without deciding when it should act.

Both initial creation and reproduction must use this helper. Initial organisms
use `birth_tick=0`; offspring use the current simulation tick.

### Step 8: Add Unique Neighboring-Position Logic

Add to `World`:

```python
def neighboring_positions(
    self,
    x: int,
    y: int,
) -> list[tuple[int, int]]:
```

Generate north, east, south, and west through `wrap_position()`, then remove
duplicates while preserving that discovery order.

Examples:

- A normal world position has four unique neighbors.
- A `1x1` world has one unique wrapped position: the parent's occupied position.
- Narrow worlds may have fewer than four unique positions.

### Step 9: Add a Separate Reproduction Phase

The Phase 1 tick order is:

```text
Sense
  -> Decide
  -> Execute normal action
  -> Pay metabolism and action cost
  -> Process death
  -> Finish all starting organisms
  -> Reproduction phase for survivors
  -> Add newborns
  -> Record completed-tick metrics
  -> Next tick
```

Only surviving organisms are considered. Newborns are kept separate until all
eligible parents have completed their attempt.

### Step 10: Build Reproduction Occupancy

At the start of the reproduction phase:

```python
occupied_positions = {
    (organism.x, organism.y)
    for organism in surviving_organisms
}
```

This set reflects reproduction-phase occupancy only. It may contain fewer entries
than surviving organisms because pre-existing overlaps are deferred technical
debt.

### Step 11: Build and Shuffle Eligible Parents

Build eligibility without using the RNG. Copy and shuffle only the eligible
parents:

```python
eligible_parents = [
    organism
    for organism in surviving_organisms
    if organism.energy >= organism.genome.reproduction_threshold
    and organism.energy >= self.config.reproduction_energy_cost
]

reproduction_order = eligible_parents.copy()
if reproduction_order:
    self.random.shuffle(reproduction_order)
```

Do not shuffle `self.organisms` or `surviving_organisms`. If the eligible list is
empty, skip the shuffle and the reproduction loop.

### Step 12: Implement `_try_reproduce()`

Add:

```python
def _try_reproduce(
    self,
    parent: Organism,
    occupied_positions: set[tuple[int, int]],
) -> Organism | None:
```

The method must:

1. Recheck threshold and cost affordability defensively.
2. Get unique wrapped neighboring positions.
3. Filter out every currently occupied or reserved position.
4. Return `None` without changing energy if no position is available.
5. Choose one available position using the simulation RNG.
6. Save the parent's pre-reproduction energy for the conservation check.
7. Subtract the reproduction cost.
8. Split the remaining energy equally.
9. Deep-copy the parent's genome.
10. Give the child the parent's direction.
11. Set the child's `parent_id` and `birth_tick`.
12. Build and return the child.
13. Reserve the newborn position immediately.
14. Increment the parent's offspring count and all birth metrics exactly once.
15. Assert, with floating-point tolerance, that parent and child energy sum to
    the parent's pre-reproduction energy minus the configured cost.

No energy is charged until space has been found and a birth will succeed.

### Step 13: Keep Newborns Separate Until the Phase Ends

Use:

```python
newborns: list[Organism] = []
```

After all eligible parents have been processed:

```python
self.organisms = surviving_organisms + newborns
```

This ensures newborns do not act or reproduce on their birth tick.

### Step 14: Extend Reproduction Metrics

Add to `OrganismMetrics`:

```python
parent_id: int | None
birth_tick: int
offspring_count: int = 0
```

Add to `TickMetrics`:

```python
births: int = 0
```

Add to `SimulationMetrics`:

```python
total_births: int = 0
first_birth_tick: int | None = None
last_birth_tick: int | None = None
peak_population: int = 0
```

Initialize `peak_population` to the Big Bang population after initial organisms
are created. After each completed tick, update it from the ending population.

For every successful birth:

- increment the tick birth count;
- increment total births;
- increment the parent's offspring count;
- set the first birth tick if this is the first birth;
- update the last birth tick.

### Step 15: Correct Population and Death Accounting

Deaths must be calculated before newborns are included:

```python
deaths = starting_population - len(surviving_organisms)
births = len(newborns)
ending_population = len(surviving_organisms) + births
```

Do not continue using `starting_population - ending_population` as the death
count after reproduction exists.

### Step 16: Update Progress Output

Include births:

```text
Tick 60 | Population 112 | Births 4 | Deaths 1 | Ate 15.00 | Moves 18
```

### Step 17: Add Reproduction Results to the Final Report

Report:

```text
Total births
Peak population
Organisms that reproduced
First birth tick
Last birth tick
Most offspring by one organism
Parent ID(s) with most offspring
```

Use `NONE` consistently when a run contains no births or reproducing parents.

### Step 18: Extend Consistency Checks

For every tick, verify:

```python
ending_population == starting_population - deaths + births
```

For the experiment, verify:

```python
total_births == next_organism_id - initial_population
```

Verify:

```python
sum(
    metrics.offspring_count
    for metrics in organism_metrics.values()
) == total_births
```

Also verify:

- the sum of per-tick births equals total births;
- every non-initial organism has a valid recorded parent;
- initial organisms have `parent_id=None` and `birth_tick=0`;
- each child has `birth_tick >= 1`;
- action totals still equal the sum of starting populations, proving newborns did
  not act during their birth tick;
- per-birth energy conservation holds within a small floating-point tolerance.

Do not add a global unique-occupancy assertion in this branch.

## Automated Test Plan

### Configuration Tests

Verify:

- default threshold and cost;
- rejection of negative or non-finite thresholds;
- rejection of negative or non-finite costs;
- a parent that meets its threshold but cannot afford the cost does not reproduce.

### Genome Tests

Verify:

- reproduction threshold propagation from configuration;
- equal copied values;
- different `Genome` objects;
- different outer and nested weight dictionaries;
- mutation of the child's copied weights cannot change the parent's weights.

### Neighbor Tests

Verify:

- north/east/south/west order;
- toroidal wrapping;
- duplicate removal with stable discovery order;
- `1x1`, `1x2`, `2x1`, and ordinary world dimensions.

### Forced-Reproduction Test

Use:

```python
world_width=5
world_height=5
initial_organisms=1
initial_organism_energy=100.0
initial_reproduction_threshold=90.0
reproduction_energy_cost=0.0
```

Verify:

- different permanent organism IDs;
- `child.parent_id == parent.organism_id`;
- initial parent `birth_tick == 0`;
- child `birth_tick == 1`;
- equal genome values with independent objects and dictionaries;
- inherited direction;
- equal post-reproduction energy;
- one birth at most;
- child action counts remain zero on tick 1;
- the child first becomes eligible to act on tick 2.

### Reproduction-Cost Test

Use a nonzero cost and verify:

```python
parent_after + child_energy == parent_before - reproduction_energy_cost
```

Also verify that no-space and insufficient-energy failures charge no cost.

### No-Space Test

Use a `1x1` world with reproduction enabled. Expect:

```text
Births: 0
Population: 1
```

The parent's energy must remain unchanged by the failed reproduction attempt.

### Provisional-Priority and Reservation Tests

Verify:

- eligible parents are shuffled through the simulation-owned RNG;
- the living population list is not reordered;
- a reserved newborn position cannot be claimed twice;
- blocked parents retain their energy;
- stable organism IDs do not create fixed birth priority;
- identical seeds produce identical reproduction results.

These tests validate the Phase 1 fallback, not a permanent conflict-resolution
contract.

### Metrics and Reporting Tests

Verify:

- birth, death, and ending-population accounting;
- total and per-parent offspring counts;
- first and last birth ticks;
- initial and updated peak population;
- zero-birth reports use `NONE` where appropriate;
- all reproduction consistency checks pass.

## Experiment Plan

Use the normal experiment configuration:

```python
world_width=40
world_height=40
initial_organisms=100
initial_organism_energy=100.0
initial_reproduction_threshold=150.0
reproduction_energy_cost=0.0
```

Run two named experiments:

1. **Seed 1: productive reproduction experiment.** The reproduction-free
   baseline reaches the proposed threshold and is expected to exercise births.
2. **Seed 3: zero-birth control.** The current reproduction-free baseline does
   not reach the threshold and should demonstrate that Phase 1 does not alter a
   run before any organism becomes eligible.

For each seed, run the simulation twice and verify deterministic replay. Compare:

- total births;
- first and last birth ticks;
- peak and final population;
- deaths and extinction/final tick;
- total environmental energy consumed;
- action totals;
- lineage and offspring metrics;
- final consistency checks.

## Phase 1 Completion Criteria

Reproduction Phase 1 is complete when:

- all automated tests pass;
- the source compiles;
- seed 1 produces deterministic births;
- seed 3 remains a deterministic zero-birth control unless other approved model
  changes alter its baseline;
- newborns never act or reproduce on their birth tick;
- reproduction preserves energy apart from its configured cost;
- reproduction never places two newborns into the same reserved position;
- lineage and birth metrics remain internally consistent;
- the global collision limitation and mutation deferral remain clearly documented;
- no deferred behavior is introduced accidentally.
