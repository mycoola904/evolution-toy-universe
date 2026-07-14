# 05 - Organism Model

## Overview

An organism is the fundamental autonomous entity within the Evolution Toy Universe. Every organism exists entirely within the rules of the simulation and possesses no special privileges beyond those defined by its state, genome, and interaction with the environment.

Organisms are intentionally simple. They do not contain predefined instincts, goals, or intelligence. Every observable behavior emerges from the interaction between their internal neural system, stored energy, inherited genome, and surrounding environment.

The simulation never assigns purpose to an organism. It simply executes the same deterministic rules for every organism on every simulation tick.

---

# 1. Organism Identity

Every organism maintains a minimal set of state that uniquely defines it within the simulation.

Each organism contains:

- Unique identifier
- Current position
- Current facing direction
- Stored energy
- Age
- Genome
- Neural system
- Alive/Dead state

This information completely describes an organism at any instant during the simulation.

No organism possesses hidden information or receives privileged access to the world beyond what is explicitly represented by these properties.

---

# 2. Physical Body

Version 1 organisms occupy exactly one world cell.

Organisms have:

- No body segments
- No limbs
- No size variation
- No momentum
- No mass
- No physical inventory

An organism's location is simply the grid cell it currently occupies.

Its orientation determines the direction considered "forward" for movement and sensing.

Future versions of the simulation may introduce larger or multicellular organisms, but the initial implementation intentionally minimizes physical complexity to maximize understanding of emergent behavior.

---

# 3. Internal State

Each organism maintains a small amount of internal state that changes throughout its lifetime.

Initially this consists of:

- Stored Energy
- Age

Stored energy represents the organism's ability to continue existing and perform actions.

Age represents the number of simulation ticks since creation.

Additional state variables should only be introduced when necessary to support new simulation mechanics.

The guiding principle is that every additional variable increases simulation complexity and should therefore justify its existence.

---

# 4. Life Cycle

Every organism progresses through the same simple life cycle.

```
Creation

↓

Alive

↓

(Optional Reproduction)

↓

Death

↓

Removal
```

No organism possesses developmental stages such as juvenile or adult.

Instead, life history emerges naturally from the interaction between energy, age, reproduction, and environmental conditions.

---

# 5. Actions

During each simulation tick, an organism may perform at most one action selected by its neural system.

The initial action set consists of:

- Move Forward
- Rotate Left
- Rotate Right
- Consume Environmental Resource
- Reproduce
- Do Nothing

Each action has a defined energy cost.

Actions never succeed automatically.

For example, a movement action may fail because another organism occupies the destination cell.

Likewise, consuming food may fail if no usable resource exists in the current location.

The organism still performed the action; the environment simply determined the outcome.

---

# 6. Energy

Energy is the fundamental resource required for life.

Every organism stores an internal energy reserve.

Energy is consumed by:

- Existing each simulation tick
- Movement
- Rotation
- Reproduction
- Other future biological actions

Energy is obtained by consuming environmental resources.

The simulation does not distinguish between biological concepts such as hunger, fatigue, or health.

All of these effects are represented solely through available energy.

This intentionally reduces multiple biological systems into a single conserved quantity.

---

# 7. Sensors

Organisms possess only limited knowledge of the world.

They never receive complete information about the environment.

Instead, the neural system receives a small collection of sensory inputs representing the organism's immediate internal state and local surroundings.

Possible Version 1 inputs include:

- Current stored energy
- Current age
- Resource present in current cell
- Resource present in the forward cell
- Occupancy of the forward cell
- Current facing direction

The exact sensor set is intentionally minimal.

An organism has no global awareness of the world, no knowledge of distant resources, and no information about other organisms beyond what its immediate sensors can detect.

Version 1 intentionally provides no explicit random sensory input. Given identical initial conditions and the same simulation seed, organisms will receive identical sensory information and produce identical behavior. This determinism supports reproducible experiments and simplifies understanding of the simulation.

If future experimentation demonstrates that additional environmental variability is beneficial, such behavior should ideally arise from changes within the environment itself rather than through artificial randomness introduced directly into the organism's sensory system.

---

# 8. Effectors

Effectors are the mechanisms through which an organism influences the world.

The neural system selects an output action.

The simulation then attempts to execute that action according to the rules of the environment.

The initial effectors correspond directly to the available actions:

- Move
- Rotate
- Consume Resource
- Reproduce
- Remain Idle

Effectors contain no intelligence.

They simply execute whatever action the neural system requests.

---

# 9. Genome Relationship

Every organism possesses a genome inherited from its parent or generated during initialization.

The genome defines the inherited characteristics of the organism.

Examples may include:

- Neural network structure
- Neural connection weights
- Mutation parameters
- Reproductive characteristics
- Sensor configuration
- Effector configuration

The genome itself is described in detail within the Genome and Reproduction documents.

This document defines only the organism's relationship to that inherited information.

---

# 10. Death

Death occurs whenever an organism can no longer satisfy the minimum requirements for continued existence.

Version 1 defines a single cause of death:

- Stored energy reaches zero.

Additional causes may be introduced in future versions, including environmental hazards or predation.

Upon death:

- The organism performs no further actions.
- It is removed from the active organism list.
- Its occupied world cell becomes available.

Whether death returns energy to the environment is intentionally left to the Energy Model.

---

# 11. Design Philosophy

The organism model is intentionally minimal.

The simulation does not assign intelligence, motivation, curiosity, fear, or desire to an organism.

Instead, every behavior arises through repeated execution of simple rules.

An organism does not "want" food.

It does not "search" for mates.

It does not "avoid" danger.

Rather, its neural system transforms sensory inputs into actions according to its inherited genome and current internal state.

Observers may describe these behaviors using human language, but the simulation itself contains no concepts of intention or purpose.

This philosophy supports one of the project's central principles:

> Nothing is Special.

Every organism is governed by the same rules.

Every organism receives the same opportunities.

Every organism succeeds or fails solely through interaction with its environment and the inherited structure of its genome.

Complexity is expected to emerge naturally from these simple foundations rather than from increasingly sophisticated built-in behaviors.