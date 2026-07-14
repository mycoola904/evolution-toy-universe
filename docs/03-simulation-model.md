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

## 2. Simulation Loop

The Toy Universe advances through a deterministic sequence of phases during each simulation tick. Every organism and world object observes the same world state at the beginning of the tick, computes its next action independently, and then all state changes are applied simultaneously.

This synchronous update model prevents organisms from gaining an advantage simply because they were processed earlier in an iteration.

### Simulation Tick

Each tick proceeds through the following phases:

1. **Observe**

   * Every organism gathers information from its local environment.
   * Sensors produce inputs for the organism's neural system.
   * No world state is modified during this phase.

2. **Think**

   * Each organism processes its sensory inputs.
   * The neural system produces a set of intended actions.
   * Decisions are recorded but not yet executed.

3. **Act**

   * All intended actions are applied simultaneously.
   * Typical actions may include:

     * Movement
     * Turning
     * Eating
     * Attacking
     * Reproducing
     * Communication
     * Remaining idle

4. **Resolve Interactions**

   * Conflicts resulting from simultaneous actions are resolved.
   * Examples include:

     * Multiple organisms attempting to enter the same location.
     * Multiple organisms attempting to consume the same resource.
     * Simultaneous attacks.
   * Resolution rules are deterministic and documented separately.

5. **Update Energy**

   * Energy costs for actions are applied.
   * Energy gained from food or other sources is added.
   * Organisms with insufficient energy may die.
   * Environmental energy sources may regenerate or decay according to world rules.

6. **Life Cycle**

   * Births are finalized.
   * Deaths are processed.
   * Organisms are added to or removed from the world.
   * Population statistics are updated.

7. **Advance Time**

   * The simulation tick counter is incremented.
   * The next tick begins.

### Design Principles

The simulation loop should satisfy several important properties:

* **Deterministic** — Given the same initial world state and random seed, the simulation always produces the same results.

* **Synchronous** — Every organism acts from the same snapshot of the world.

* **Modular** — Individual phases can evolve without changing the overall structure of the loop.

* **Simple** — The loop should remain easy to understand and reason about. Additional complexity belongs inside the individual subsystems rather than the scheduler itself.

The simulation loop intentionally contains no organism-specific behavior. It merely defines the order in which the universe evolves.
