# Simulation Observability Implementation Plan

## Goal

The purpose of this branch is to improve visibility into what happens during a simulation without changing organism behavior.

At the end of an experiment, the report should answer:

- Did organisms eat after tick 1?
- How often was `EAT` attempted successfully or unsuccessfully?
- Did any organisms move?
- Which organism moved the most?
- Which organism ate the most?
- What was the last successful eating tick?
- Which organism or organisms survived the longest?
- What genome did the last survivor have?
- How much world energy remained stranded?
- How did actions divide among `WAIT`, `EAT`, movement, and turning?

The guiding rule for this branch is:

> Observe what the organisms do, but do not help them do it.

---

## Phase 1: Remove the noisy per-organism output

The current `_print_organism_step()` output is too detailed for experiments with large populations.

### Remove

Delete the following per-organism output:

- Direction
- Selected action
- Previous and final locations
- Energy cost
- Current energy
- Sensed cell energy
- Normalized sensor values
- Neural activations
- Genome weights during each tick

Remove the `show_details` argument from `Simulation.step()`:

```python
def step(self) -> None:
```

Delete `_print_organism_step()` entirely, including its commented-out genome and activation code.

In `main.py`, change:

```python
simulation.step(show_details=True)
```

to:

```python
simulation.step()
```

### Result

A normal experiment should produce:

1. Occasional compact progress lines.
2. One detailed final experiment report.

---

## Phase 2: Give every organism a permanent ID

The loop index cannot identify an organism reliably because indexes change when dead organisms are removed.

### Changes to `Organism`

Add a required ID:

```python
organism_id: int
```

Store it:

```python
self.organism_id = organism_id
```

### Changes to `Simulation`

Add:

```python
self.next_organism_id = 0
```

When creating an organism:

```python
organism_id = self.next_organism_id
self.next_organism_id += 1
```

Pass that ID into `Organism`.

This centralized ID assignment will also work later when reproduction creates new organisms.

---

## Phase 3: Add structured metrics classes

Create:

```text
src/domain/simulation_metrics.py
```

This file should contain three dataclasses.

### `OrganismMetrics`

One record per organism:

```python
from dataclasses import dataclass
from domain.action import Action
from domain.genome import Genome


@dataclass
class OrganismMetrics:
    organism_id: int
    genome: Genome
    action_counts: dict[Action, int]

    successful_eats: int = 0
    unsuccessful_eats: int = 0
    energy_eaten: float = 0.0

    first_successful_eat_tick: int | None = None
    last_successful_eat_tick: int | None = None

    peak_energy: float = 0.0
    death_tick: int | None = None
    final_action: Action | None = None
```

Movement does not need a separate counter because it can be obtained from:

```python
action_counts[Action.MOVE_FORWARD]
```

An organism “ever moved” when that count is greater than zero.

### `TickMetrics`

One compact record per tick:

```python
@dataclass
class TickMetrics:
    tick: int
    starting_population: int
    action_counts: dict[Action, int]

    ending_population: int = 0
    deaths: int = 0

    successful_eats: int = 0
    unsuccessful_eats: int = 0
    energy_eaten: float = 0.0
```

Keeping tick history will make later charts and population graphs possible without redesigning the simulation again.

### `SimulationMetrics`

The experiment-wide record:

```python
@dataclass
class SimulationMetrics:
    organism_metrics: dict[int, OrganismMetrics]
    tick_history: list[TickMetrics]
    action_counts: dict[Action, int]

    successful_eats: int = 0
    unsuccessful_eats: int = 0
    total_energy_eaten: float = 0.0

    tick_one_energy_eaten: float = 0.0
    after_tick_one_energy_eaten: float = 0.0

    first_successful_eat_tick: int | None = None
    last_successful_eat_tick: int | None = None
```

### Fresh action counters

Use a helper function so each metrics record receives its own dictionary:

```python
def new_action_counts() -> dict[Action, int]:
    return {
        action: 0
        for action in Action
    }
```

---

## Phase 4: Make `EAT` report what happened

The current `Organism.eat()` calculates `energy_eaten`, but does not return it.

Change it to:

```python
def eat(self, cell: Cell) -> float:
    energy_eaten = cell.energy
    self.energy += energy_eaten
    cell.energy -= energy_eaten
    return energy_eaten
```

This does not change eating behavior. It only reports the result.

Change `Simulation.execute_action()` to return the amount eaten:

```python
def execute_action(
    self,
    organism: Organism,
    action: Action,
) -> float:
```

For `EAT`:

```python
return organism.eat(cell)
```

For all other actions:

```python
return 0.0
```

Then `step()` can distinguish:

```python
successful_eat = (
    action == Action.EAT
    and energy_eaten > 0.0
)
```

from:

```python
unsuccessful_eat = (
    action == Action.EAT
    and energy_eaten == 0.0
)
```

This will also correctly capture two organisms trying to eat the same cell during one tick. The first may succeed and the second may record an unsuccessful attempt.

---

## Phase 5: Register each organism’s metrics at creation

When `create_initial_organism()` creates an organism, also create its metrics record:

```python
self.metrics.organism_metrics[organism_id] = (
    OrganismMetrics(
        organism_id=organism_id,
        genome=genome,
        action_counts=new_action_counts(),
        peak_energy=energy,
    )
)
```

The metrics dictionary preserves the records of dead organisms after they are removed from `self.organisms`.

A separate `dead_organisms` list is not necessary.

---

## Phase 6: Record activity during every step

At the beginning of `step()`:

```python
tick_metrics = TickMetrics(
    tick=self.tick,
    starting_population=len(self.organisms),
    action_counts=new_action_counts(),
)
```

### Record the selected action

After choosing an action:

```python
tick_metrics.action_counts[action] += 1
self.metrics.action_counts[action] += 1
organism_metrics.action_counts[action] += 1
```

Also record:

```python
organism_metrics.final_action = action
```

### Execute the action

```python
energy_eaten = self.execute_action(
    organism=organism,
    action=action,
)
```

### Record eating

When the action is `EAT` and `energy_eaten > 0`:

- Increment successful-eat counts.
- Add the quantity eaten.
- Record the first successful eating tick when it is still `None`.
- Update the last successful eating tick.
- Add the amount to either:
  - `tick_one_energy_eaten`, or
  - `after_tick_one_energy_eaten`.

When the action is `EAT` and nothing was available:

- Increment unsuccessful-eat counts.

### Record peak energy

Update peak stored energy immediately after the action and before metabolic cost:

```python
organism_metrics.peak_energy = max(
    organism_metrics.peak_energy,
    organism.energy,
)
```

This captures the highest achieved energy, including food just consumed.

### Record death

After the energy burn:

```python
if organism.energy <= 0.0:
    organism.energy = 0.0
    organism_metrics.death_tick = self.tick
```

Continue using the survivor-list approach. Do not remove organisms from `self.organisms` while iterating.

### Finalize the tick

After the organism loop:

```python
tick_metrics.ending_population = len(
    surviving_organisms
)

tick_metrics.deaths = (
    tick_metrics.starting_population
    - tick_metrics.ending_population
)

self.metrics.tick_history.append(tick_metrics)
```

Have `step()` return the completed tick record:

```python
return tick_metrics
```

---

## Phase 7: Add compact progress output

A long simulation should not appear frozen, but it should not print every organism.

In `main.py`, choose an interval:

```python
progress_interval = 10
```

Capture the tick metrics:

```python
tick_metrics = simulation.step()
```

Print only:

- Tick 1
- Every tenth tick
- The extinction tick

Example:

```text
Tick 1   | Population 100 | Deaths 0 | Ate 487.00 | Moves 18
Tick 10  | Population 100 | Deaths 0 | Ate 22.00  | Moves 179
Tick 50  | Population 91  | Deaths 4 | Ate 3.00   | Moves 132
Tick 100 | Population 14  | Deaths 2 | Ate 0.00   | Moves 9
Tick 172 | Population 0   | Deaths 1 | Ate 0.00   | Moves 0
```

The movement number on each line should mean `MOVE_FORWARD` actions during that tick, not cumulative movement.

---

## Phase 8: Expand the final report

Retain the current environmental-energy section and add focused experiment sections.

### Experiment summary

```text
Status
Seed
World dimensions
Final tick
Initial population
Remaining population
```

Including the seed is important because experiments will be repeated with different seeds.

### Environmental energy

```text
Initial world energy
Remaining world energy
World energy consumed
Percent consumed
Percent left stranded
Energy eaten on tick 1
Energy eaten after tick 1
Percent of consumed energy eaten after tick 1
First successful EAT tick
Last successful EAT tick
```

This directly tests whether eating continued after the starting tick.

### Action totals

For every action, print the count and percentage:

```text
WAIT:          2,341  18.45%
EAT:           4,027  31.75%
MOVE_FORWARD:  1,876  14.79%
TURN_LEFT:     3,271  25.79%
TURN_RIGHT:    1,169   9.22%
```

### Eating results

```text
Total EAT attempts
Successful EAT actions
Unsuccessful EAT actions
EAT success rate
Organisms that successfully ate
Total energy eaten
```

### Movement results

```text
Total MOVE_FORWARD actions
Organisms that moved at least once
Most moves by one organism
Organism ID with the most moves
```

### Survival results

```text
Last death tick
Longest-surviving organism IDs
Number tied for longest survival
```

Several organisms may die during the final tick, so preserve ties rather than inventing one unique last survivor.

### Notable organisms

Report:

- Longest-lived organism
- Largest energy consumer
- Most mobile organism
- Highest peak-energy organism

Each entry should include:

```text
Organism ID
Death tick
Successful eats
Energy eaten
Moves
Peak energy
Final action
```

One organism may hold several of these titles.

---

## Phase 9: Print one representative last-survivor genome

To avoid printing many genomes, select one representative from the organisms tied for the final death tick.

Use this selection rule:

1. Latest death tick.
2. Greatest total energy eaten.
3. Greatest number of moves.
4. Lowest organism ID as the final deterministic tie-breaker.

Label it accurately:

```text
REPRESENTATIVE LAST-SURVIVOR GENOME
```

Then print the weights once:

```text
WAIT:
  CELL_ENERGY:    ...
  STORED_ENERGY:  ...
  BIAS:           ...

EAT:
  ...
```

Also list all IDs tied for longest survival so the report does not imply that only one organism survived to the final tick.

On a tick-limit result rather than extinction, print a representative remaining organism instead.

---

## Phase 10: Add consistency checks

Before trusting the experiments, verify these relationships at report time:

```python
successful_eats + unsuccessful_eats == total_eat_actions
```

```python
tick_one_energy_eaten + after_tick_one_energy_eaten == total_energy_eaten
```

```python
total_energy_eaten == (
    initial_world_energy - remaining_world_energy
)
```

```python
sum(all_action_counts.values()) == total_organism_turns
```

```python
sum(per_organism_action_counts) == experiment_action_counts
```

At extinction:

```python
every_organism_has_a_death_tick
```

```python
final_simulation_tick == latest_death_tick
```

During development, these can be `assert` statements. They will catch instrumentation mistakes without changing simulation behavior.

---

## Suggested implementation order

Implement and test the branch in six commits:

1. **Remove verbose organism debug output**
2. **Add stable organism IDs**
3. **Add metrics dataclasses and registration**
4. **Return energy eaten and record action/eating metrics**
5. **Add tick history and compact progress output**
6. **Expand final report and print representative survivor genome**

The first major checkpoint comes after commit 4, when the simulation can conclusively determine how much eating occurred after tick 1.
