# Simulation Model

## Purpose

Define how time advances, how the world updates, and how organisms and environment interact inside the toy universe.

## Scope

This document explains the simulation loop and update rules at a high level. More detailed rules for the world, organisms, energy, reproduction, and neural systems are defined in later model documents.

## Core Questions

- What is one “tick” of the simulation?
- What happens during each tick?
- In what order are organisms, energy, and environment updated?
- Are updates simultaneous, sequential, or staged?
- What information does an organism have access to?
- What counts as an action?
- What causes death, survival, or reproduction?
- How is randomness used?
- What data should be recorded over time?

## Initial Principle

The simulation should be simple enough to understand, but rich enough for surprising behavior to emerge.

A single tick should represent one small step of time in the toy universe. During each tick, organisms perceive their local environment, choose actions, consume or expend energy, interact with the world, and are then evaluated for survival and reproduction.

## Likely Sections

1. Time and Ticks
2. Simulation Loop
3. Update Order
4. Organism Perception
5. Organism Actions
6. Energy Accounting
7. Environment Updates
8. Reproduction and Death Checks
9. Randomness
10. Metrics and History
11. Open Design Questions

---

## 1. Time and Ticks

Time within the simulation is **discrete**. The universe exists only as a sequence of complete world states. Nothing occurs between ticks; each tick represents the transition from one fully-defined state of the world to the next.

This approach was chosen for several reasons:

- Simplicity of implementation
- Deterministic and reproducible behavior
- Elimination of race conditions caused by update order
- Straightforward save/load functionality
- Easy debugging and inspection of world state
- Scalability for future optimization or parallel execution

Each tick produces a new world state by applying the laws of the simulation to the previous state.

```
State(t + 1) = Simulation(State(t))
```

### Synchronous Updates

All organisms observe the same world state before any organism acts. No organism receives priority based on its position in memory or iteration order.

Each simulation tick consists of four phases:

1. **Perceive**
   - Every organism gathers information from the current world state.

2. **Decide**
   - Every organism independently determines its intended action.

3. **Resolve**
   - The simulation applies the rules of the universe to all intended actions simultaneously, resolving conflicts where necessary.

4. **Update**
   - Energy changes, environmental changes, births, deaths, and statistical information are finalized, producing the next world state.

This phased approach ensures that every organism operates under the same conditions during a given tick. Outcomes are determined solely by the laws of the simulation rather than by execution order, reinforcing the project's core principle that **Nothing is Special**.

# 2. Simulation Loop

The Toy Universe advances through a deterministic sequence of phases during each simulation tick. Every organism observes the same world state, independently determines its intended behavior, and then the universe resolves those intentions according to the world's rules.

This synchronous update model ensures that no organism gains an advantage simply because it happened to be processed first.

## Simulation Tick

Each simulation tick proceeds through the following phases.

### 1. Observe

Every organism gathers information from its environment.

Examples include:

* Nearby organisms
* Nearby energy sources
* Terrain
* Internal state (energy, age, health, etc.)

This phase is read-only. No world state is modified.

---

### 2. Think

Each organism processes its observations through its neural system (or whatever decision mechanism it possesses).

The result of this phase is an **intent**.

Examples of intents include:

* Move North
* Move East
* Eat
* Attack organism #42
* Reproduce
* Remain Idle

No actions are executed during this phase.

Every organism simply records what it intends to do.

---

### 3. Resolve Intent

The universe now resolves every organism's recorded intent simultaneously.

The simulation loop itself contains no special knowledge of movement, eating, combat, reproduction, or any other behavior. Instead, each subsystem is responsible for interpreting and resolving the intents relevant to it.

For example:

* The movement system resolves competing movement requests.
* The feeding system determines whether food is available to consume.
* The combat system resolves attacks.
* The reproduction system determines whether offspring can be created.

Conflicts are therefore resolved by the subsystem responsible for that behavior rather than by the simulation scheduler.

This separation keeps the simulation loop simple while allowing individual systems to evolve independently.

---

### 4. Update Energy

After all intents have been resolved:

* Energy costs are applied.
* Energy gained from food or other sources is added.
* Environmental energy may regenerate or decay.
* Organisms that can no longer sustain themselves may die.

The exact energy rules are defined by the Energy Model.

---

### 5. Life Cycle

The universe finalizes population changes.

Examples include:

* Add newly created organisms.
* Remove dead organisms.
* Update population statistics.
* Perform any bookkeeping required for the next tick.

---

### 6. Advance Time

The global simulation tick is incremented.

The next simulation cycle then begins.

---

# Design Principles

The simulation loop is intentionally minimal.

Its responsibility is only to define the order in which the universe progresses.

All domain-specific behavior belongs to the individual systems rather than the scheduler.

This provides several desirable properties:

* **Deterministic** — Given the same initial state and random seed, the simulation always produces the same result.
* **Synchronous** — Every organism observes the same world before acting.
* **Modular** — Individual systems evolve independently without requiring changes to the simulation scheduler.
* **Simple** — The scheduler remains small, predictable, and easy to reason about.

The simulation loop is therefore the heartbeat of the Toy Universe, while the individual systems define the laws by which that universe operates.


## 3. Update Order

The simulation uses a **staged synchronous update** model. During a tick, no organism directly modifies the world while decisions are being made.

Instead, the simulation proceeds in four distinct phases:

1. **Perceive**
2. **Decide**
3. **Resolve**
4. **Update**

Every organism perceives the same world state before any organism acts. Each organism then independently produces an intended action based solely on the information available during the Perceive phase.

The Resolve phase applies the laws of the universe to all intended actions simultaneously. Conflicts between organisms are resolved according to deterministic simulation rules rather than execution order.

Only after all actions have been resolved are changes committed to produce the next world state.

This staged approach ensures that no organism gains an advantage simply because it was processed earlier or later than another, reinforcing the project's guiding principle that **Nothing is Special**.

---

## 4. Organism Perception

Perception is the first phase of every simulation tick.

Each organism gathers information from the current world state within the limits of its own sensory capabilities. Organisms have no direct knowledge of future events, hidden simulation state, or the intended actions of other organisms.

Perception is intentionally local and limited. The exact sensory model—including vision, range, environmental awareness, or other inputs—is defined by the Organism Model and Neural System documents.

Within a single tick, all organisms perceive the same immutable world state before any actions are resolved.

---

## 5. Organism Actions

Following perception, each organism determines its intended action for the current tick.

An intended action represents what the organism attempts to do based on its internal state and perceived environment. Examples may include movement, feeding, reproduction, communication, or remaining idle.

Producing an intended action does not guarantee that the action succeeds. Multiple organisms may attempt incompatible actions, compete for the same resources, or interfere with one another.

The Resolve phase determines the actual outcome according to the simulation's rules.

The available action types and their detailed behavior are defined by the Organism Model.

---

## 6. Energy Accounting

Energy is the universal currency that enables all activity within the simulation.

Throughout each tick, organisms may expend energy through maintenance costs and actions while acquiring energy from successful interactions with the environment or other organisms.

Energy changes are accumulated during simulation resolution and committed during the Update phase, ensuring that all organisms are evaluated under the same rules.

The precise energy costs, transfer mechanisms, storage limits, and conservation rules are defined by the Energy Model.

---

## 7. Environment Updates

The environment evolves alongside the organisms as part of each simulation tick.

Changes to environmental state occur only after organism actions have been resolved. These changes may include resource consumption, resource regeneration, environmental transformations, or other world-level processes.

Environmental updates are governed by the same simulation principles as organism updates: the next world state is derived entirely from the previous state and the resolved outcomes of the current tick.

Detailed environmental behavior is defined by the World Model and Energy Model.

---

## 8. Reproduction and Death Checks

The final stage of each simulation tick evaluates organism survival and reproduction.

Organisms that no longer satisfy the simulation's survival conditions are removed from the next world state. Organisms meeting the conditions for reproduction may generate offspring according to the reproduction rules.

New offspring become part of the newly created world state and begin participating in the simulation on the following tick.

The exact conditions governing reproduction, inheritance, mutation, lifespan, and death are defined by the Reproduction Model.

## 9. Randomness

The simulation is intentionally **deterministic wherever possible**. Given the same initial world state and the same sequence of random events, the simulation will always produce the same future world states.

Randomness is not used to simplify implementation or to make organism behavior appear more interesting. Instead, randomness represents a deliberate property of the toy universe and is introduced only where it serves a fundamental role.

### Initial World Generation

The creation of a new universe may include random processes such as:

- Initial placement of organisms
- Initial distribution of energy resources
- Initial environmental features

Once the initial world has been generated, the simulation proceeds according to the laws of the universe.

### Mutation

Random mutation is introduced during reproduction.

Mutations provide the variation required for evolutionary processes while preserving deterministic behavior throughout the remainder of the simulation. Every reproducing organism is subject to the same mutation rules and probabilities.

The exact mutation mechanisms and probabilities are defined in the Reproduction Model.

### Deterministic Behavior

Outside of world initialization and mutation, the simulation is deterministic.

Given identical inputs, organisms will:

- Perceive the same information
- Produce the same intended actions
- Experience the same action resolutions
- Gain and expend the same energy
- Produce the same changes to the environment

Behavior should emerge from the organism's internal structure and the laws of the simulation rather than from random decision making.

### Reproducibility

The simulation should support reproducible experiments.

By recording the initial world configuration and the sequence of random events, an identical simulation can be replayed for debugging, experimentation, and scientific comparison.

This supports the project's goal of creating a simple, understandable universe whose behavior emerges from consistent rules rather than arbitrary outcomes.