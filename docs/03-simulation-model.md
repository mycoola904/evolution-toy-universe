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