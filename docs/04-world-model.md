# 04 - World Model

## 1. Purpose

The World Model defines the physical environment in which the simulation takes place. It describes the structure of space, how locations are represented, and the local state that exists at each position within the universe.

The world itself is not an active participant with goals or intentions. It provides the environment in which organisms live, move, consume energy, reproduce, and interact. The rules governing environmental behavior are intentionally simple, allowing complex system behavior to emerge from the interaction between organisms and their surroundings.

Like every other component of the Toy Universe, the world is governed by deterministic rules. Given the same initial state and random seed, the world will evolve identically from one simulation run to the next.

---

## 2. Space

The Toy Universe is represented as a two-dimensional grid of discrete locations. Each location is represented by a single cell. The world has fixed dimensions that are established when the simulation begins.

The world uses a toroidal topology. Movement beyond the left or right edge wraps around to the opposite side, and movement beyond the top or bottom edge behaves the same way. As a result, the world has no boundaries or corner cells that require special behavior.

Using a toroidal world simplifies the simulation by ensuring that every location has the same neighborhood structure and that no position receives special treatment because of its location. This supports the project's core principle that no object or location is inherently special.

---

## 3. Cells

Each location within the world is represented by a single cell. A cell is the fundamental unit of space within the simulation and serves as a passive container for local environmental state.

Cells are abstract locations rather than representations of real-world physical dimensions. Their visual size is determined entirely by the user interface and has no effect on the simulation itself.

In the initial implementation, each cell stores only the information required by the simulation:

- Environmental energy available at that location.
- An optional reference to the organism currently occupying the cell.

A cell may contain environmental energy whether or not it is occupied, but it may contain no more than one organism at a time.

Cells do not implement environmental behavior themselves. They simply store local state. The World Model is responsible for applying the rules that govern energy, occupancy, and all other environmental changes.

---

## 4. Terrain Types

The initial world contains a single terrain type with identical behavior at every location. No cell possesses unique movement costs, resource generation rates, or environmental effects.

Additional terrain types, such as water, rock, forest, or other environmental features, may be introduced in future versions only when they support meaningful new behaviors within the simulation.

---

## 5. Environmental Resources

The world stores energy in the environment rather than representing specific physical resources such as food, plants, or minerals.

Environmental energy is the primary resource available to organisms. Organisms obtain energy by interacting with the cells they occupy, transferring energy from the environment into themselves according to the rules defined by the Energy Model.

Using an abstract representation of energy keeps the simulation independent of any particular biological interpretation while preserving the essential concept of energy transfer.

---

## 6. Environmental Dynamics

The initial environment follows a single, simple rule for energy generation.

During each simulation tick, every cell has a fixed probability of gaining one unit of environmental energy. This probability is uniform across the entire world and is independent of whether the cell is currently occupied.

This simple regeneration rule provides a continuous source of environmental energy while allowing patterns of abundance and scarcity to emerge naturally through organism behavior.

More sophisticated environmental dynamics, such as regional variation, diffusion, seasonal effects, or weather, may be added in future versions without altering the underlying structure of the world.

---

## 7. Occupancy Rules

Each cell may contain zero or one organism.

Organisms and environmental energy may occupy the same cell simultaneously. The presence of an organism does not prevent environmental energy from existing or regenerating within that location.

Conflicts arising from multiple organisms attempting to occupy the same cell are resolved according to the rules defined by the Simulation Model.

---

## 8. World Initialization

At the beginning of each simulation, the world is generated deterministically from its initialization parameters.

These parameters include:

- World dimensions.
- Random seed.
- Initial environmental energy distribution.
- Initial organism placement.

Given identical initialization parameters, the world will always be created in exactly the same state.

---

## 9. World Invariants

The following conditions are expected to remain true throughout every simulation:

- Every coordinate within the world contains exactly one cell.
- Every organism occupies exactly one valid cell.
- No cell contains more than one organism.
- Environmental energy is never negative.
- All organism locations remain valid within the toroidal world.

These invariants provide a foundation for validating the correctness of the simulation throughout its execution.

---

## 10. Future Extensions

The World Model is intentionally designed to accommodate future environmental complexity without requiring changes to its core structure.

Potential future extensions include:

- Multiple terrain types.
- Environmental hazards.
- Weather systems.
- Seasonal variation.
- Rivers and flowing resources.
- Energy diffusion.
- Chemical gradients.
- Environmental construction or modification by organisms.

These features should only be introduced when they enable meaningful new interactions or explain behaviors that cannot emerge from the simpler model.

---

## Closing Philosophy

The initial World Model is intentionally minimal. Its purpose is not to simulate a realistic physical environment, but to provide the simplest possible universe capable of supporting emergent behavior.

Additional environmental complexity should be introduced only when it enables new forms of interaction or explains observed behaviors that cannot arise from the existing rules. In keeping with the project's core principles, complexity should emerge through the interaction of simple rules rather than through increasingly elaborate world mechanics.