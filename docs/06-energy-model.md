# 06 - Energy Model

## Purpose

Energy is the fundamental currency of the Toy Universe.

Every organism exists because it possesses energy, survives by acquiring energy, and ceases to exist when its energy is exhausted. Every action performed by an organism has an energetic cost, and every opportunity within the environment ultimately represents the acquisition or loss of energy.

The goal of this model is to define a simple, deterministic energy system capable of producing complex emergent behavior without introducing unnecessary biological concepts such as health, hunger, stamina, nutrition, or multiple resource types.

---

# Design Goals

The energy system should satisfy the following principles:

- Energy is the only resource in the simulation.
- Every organism continuously consumes energy simply by existing.
- Every meaningful action has an additional energy cost.
- Organisms survive by maintaining a positive energy balance.
- Energy moves through the universe according to deterministic rules.
- Energy should be easy to observe and reason about.
- Interesting behavior should emerge from energy economics rather than special-case rules.

---

# Energy as the Universal Currency

The Toy Universe models only a single resource:

**Energy.**

Energy represents every biological necessity.

Rather than separately modeling:

- Food
- Hunger
- Health
- Fat reserves
- Nutrients
- Reproduction resources
- Stamina

all of these concepts are intentionally abstracted into a single energy value.

An organism with more stored energy simply has greater ability to survive, move, reproduce, and recover from poor decisions.

This simplification allows surprisingly complex strategies to emerge while keeping the simulation understandable.

---

# The Source of Energy

The Toy Universe begins with a single external assumption:

**Energy enters the world through a simple, configurable environmental process.**

Everything else within the simulation is simply the movement of that energy between the environment and organisms.

The simulation does not attempt to model the origin of this energy. Like the laws of physics themselves, this is accepted as a foundational property of the universe.

Once introduced, energy follows deterministic rules that govern how it is stored, transferred, consumed, and eventually recycled.

---

# Environmental Energy

The environment stores energy independently of organisms.

Environmental energy exists as discrete quantities located within world cells.

Examples might represent:

- sunlight
- nutrients
- food particles
- chemical energy

The simulation intentionally does not distinguish between these sources.

Each energy-containing cell stores a numeric energy value.

Example:

```
Cell (12,8)

Terrain : Plain
Energy  : 17
```

When an organism consumes energy from a cell, the stored amount decreases accordingly.

---

# Environmental Energy Generation

Version 1 introduces energy into the world through a simple regeneration process.

One possible implementation is:

- each simulation tick
- randomly select a configurable number of cells
- add a configurable amount of energy

This continually replenishes the environment while remaining intentionally simple.

Future versions may replace this mechanism with more sophisticated ecological systems such as photosynthesis or nutrient cycles.

---

# Organism Energy Storage

Every organism maintains a single energy value.

Example:

```
Energy = 42
```

This represents the organism's complete metabolic reserve.

Energy increases through consumption.

Energy decreases through metabolism and activity.

The maximum energy an organism may store is configurable.

If an organism attempts to consume more energy than it can store, it only consumes the amount that fits within its remaining capacity.

Any excess energy remains in the environment.

This preserves the conservation of energy within the simulation.

---

# Basal Metabolism

Simply remaining alive consumes energy.

Every simulation tick:

```
energy -= basal_metabolism
```

This cost is paid regardless of the organism's chosen action.

Without continual access to environmental energy, every organism will eventually exhaust its reserves and die.

---

# Additional Action Costs

Beyond basal metabolism, actions may consume additional energy.

Typical examples include:

| Action | Additional Cost |
|----------|----------------:|
| Wait | 0 |
| Rotate | 1 |
| Move | 2 |
| Consume | 1 |
| Reproduce | configurable |

The Wait action represents taking no additional action during the current tick.

Waiting still incurs basal metabolism because the organism continues to exist.

The exact numerical costs are implementation parameters rather than biological constants.

The important design principle is that every active behavior carries an energetic tradeoff.

---

# Energy Accounting

Each simulation tick follows a simple accounting model.

```
energy -= basal_metabolism

energy -= action_cost
```

Example:

```
Wait

Basal metabolism = 1
Wait cost = 0

Total energy loss = 1
```

```
Move

Basal metabolism = 1
Move cost = 2

Total energy loss = 3
```

This separation keeps the simulation easy to understand while allowing waiting itself to become a potentially successful evolutionary strategy.

---

# Energy Consumption

If an organism occupies a cell containing environmental energy, it may consume part or all of that energy.

Consumption transfers energy:

```
Environment → Organism
```

Example:

Before:

```
Cell Energy = 12
Organism Energy = 18
```

Consume 5

After:

```
Cell Energy = 7
Organism Energy = 23
```

No energy is created.

Only transferred.

---

# Energy Transfer

Energy moves through the simulation by only a few mechanisms.

- Environmental generation
- Organism consumption
- Basal metabolism
- Additional action costs
- Reproduction
- Death

Keeping the list intentionally small makes the simulation easier to understand, implement, and debug.

---

# Death

An organism dies when:

```
Energy <= 0
```

Death immediately removes the organism from the simulation.

No separate health model is required.

---

# Energy Conservation

Within the Toy Universe, energy should generally be conserved.

Energy enters the universe only through environmental generation.

Energy moves between organisms and the environment through deterministic transfer.

Energy leaves the system only through explicitly defined losses such as metabolic expenditure or configurable inefficiencies.

Maintaining approximate conservation makes the simulation easier to reason about while preserving a renewable ecosystem.

---

# Capability Costs

Every organism capability has an associated energy cost. Enhanced sensing, movement, processing, or any future capability is never free. Organisms with greater capabilities therefore require more energy to maintain and operate.

This principle creates natural evolutionary tradeoffs. A mutation that increases an organism's capability may improve its chances of finding resources or making better decisions, but it also increases the energy required to survive. Likewise, a mutation that reduces a capability may decrease performance while lowering energy consumption.

The Energy Model intentionally defines only this relationship. The exact cost functions for individual capabilities (such as sensing range, neural processing, or movement) are implementation details and may be tuned as the simulation evolves.

This ensures that no capability is inherently "better." Whether a mutation is advantageous depends entirely on the environment and the balance between its benefits and its energy cost.

---

# Tunable Parameters

The following values should remain configurable.

- Basal metabolism
- Rotate cost
- Move cost
- Consume cost
- Reproduction cost
- Maximum organism energy
- Environmental generation rate
- Environmental generation amount
- Maximum environmental energy per cell
- Death recovery percentage

Keeping these values configurable allows experimentation without changing simulation logic.

---

# Visualization

Energy should be directly observable.

Possible visualizations include:

- Cell color intensity proportional to stored energy
- Organism color intensity proportional to stored energy
- Optional energy overlays
- Population energy statistics
- World energy heat maps

Visualization should make it possible to understand *why* organisms survive or fail.

---

# Future Extensions

The Version 1 energy model intentionally remains minimal.

Possible future additions include:

- photosynthetic organisms
- decomposers
- predator/prey energy transfer
- energy leakage
- terrain-dependent metabolism
- seasonal energy cycles
- environmental diffusion
- organism-generated waste
- alternative energy storage strategies
- decomposition and energy recovery from dead organisms

These should only be introduced if they produce meaningful emergent behavior while preserving the project's principle of simplicity.

---

# Summary

The Energy Model defines the economy of the Toy Universe.

Energy enters the universe through a simple environmental process, flows through organisms as they survive and reproduce, and ultimately returns to the environment according to deterministic rules.

By reducing every biological process to the acquisition, storage, transfer, and expenditure of a single universal resource, the simulation remains simple while providing fertile ground for complex emergent evolution.