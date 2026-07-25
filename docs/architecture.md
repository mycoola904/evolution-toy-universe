# Evolution Toy Universe Design

## 1. Introduction

The Evolution Toy Universe is a simulation designed to explore how complex behavior can emerge from a small set of simple rules.

Rather than modeling biology in detail, the project seeks to create an artificial world governed by consistent physical laws. Organisms exist within this world, compete for energy, reproduce with mutation, and evolve over time. The goal is to observe the emergence of increasingly successful behaviors without hard-coding intelligence or strategy.

This document provides a high-level overview of the system architecture. Detailed design decisions are documented in the individual design documents contained in the `docs/` directory.

---

## 2. System Overview

The simulation consists of four primary subsystems:

- The **Simulation Engine** controls time and coordinates each simulation tick.
- The **Domain Model** represents the world, organisms, energy, and genetics.
- The **User Interface** visualizes the simulation and allows experiments to be configured.
- The **Infrastructure Layer** provides supporting services such as configuration, logging, and persistence.

Each subsystem has a single responsibility and communicates through well-defined interfaces.

---

## 3. Overall Architecture

```
                   +----------------------+
                   |   Simulation Engine  |
                   +----------+-----------+
                              |
          +-------------------+-------------------+
          |                   |                   |
          v                   v                   v
     World Model        Organism Model     Energy Model
          |                   |                   |
          |                   v                   |
          |            Neural System              |
          |                   |                   |
          +-------------------+-------------------+
                              |
                              v
                    Reproduction & Death
                              |
                              v
                       Updated World State
                              |
                              v
                        User Interface
```

The simulation engine advances the universe one discrete tick at a time. Each tick updates the complete world state before presenting the results to the user interface.

---

## 4. Simulation Flow

Each simulation tick follows the same sequence:

1. Update environmental resources.
2. Collect organism sensory inputs.
3. Execute each organism's neural network.
4. Resolve organism actions.
5. Apply energy costs and gains.
6. Process reproduction.
7. Remove dead organisms.
8. Record simulation statistics.
9. Render the updated world.

This deterministic update cycle ensures predictable and reproducible simulations when using the same random seed.

---

## 5. Domain Model

The domain model contains the core concepts of the simulation.

### World

Represents the simulation grid, environmental energy, and spatial relationships.

### Organism

Represents an individual living entity containing:

- Position
- Energy
- Genome
- Neural network
- Orientation

### Energy

Represents the conserved resource that powers all organism activity.

### Genome

Defines inherited neural network parameters and any future inheritable traits.

### Simulation

Coordinates the complete state of the universe.

The domain model contains no user interface logic and is independent of visualization.

---

## 6. Major Components

### Simulation Engine

Responsible for:

- Advancing time
- Executing simulation ticks
- Coordinating subsystems
- Maintaining deterministic execution

### Neural System

Responsible for:

- Processing sensory inputs
- Producing action outputs
- Executing organism decision making

### User Interface

Responsible for:

- Displaying the world
- Displaying organisms
- Visual overlays
- Simulation controls
- Experiment configuration

The UI observes the simulation but does not contain simulation rules.

### Infrastructure

Responsible for:

- Configuration
- Logging
- Save/load functionality
- Random seed management
- Utility services

---

## 7. Design Philosophy

Several principles guide every design decision.

- Keep Version 1 as simple as possible.
- Complexity should emerge rather than be programmed.
- Prefer deterministic behavior.
- Separate simulation logic from presentation.
- Build modular components with clear responsibilities.
- Extend through composition rather than modification whenever practical.

These principles encourage experimentation while keeping the codebase understandable.

---

## 8. Project Layout

```
docs/
    00-project-charter.md
    01-vision.md
    02-core-principles.md
    03-simulation-model.md
    04-world-model.md
    05-organism-model.md
    06-energy-model.md
    07-reproduction.md
    08-neural-system.md
    09-ui.md
    10-technical-design.md
    11-roadmap.md
    design.md

src/
    domain/
    engine/
    ui/
    config/
    infrastructure/
```

The documentation describes the system at progressively greater levels of detail, while the source tree mirrors the major architectural responsibilities.

---

## 9. Future Evolution

The architecture intentionally supports incremental growth.

Future versions may introduce:

- Richer environments
- Additional sensors
- More sophisticated genetics
- Ecological interactions
- Improved visualization
- Experiment automation
- Performance optimizations

The core architecture should remain stable even as the simulation grows in complexity.

---

## 10. Conclusion

The Evolution Toy Universe is designed around a simple idea: a small number of understandable rules can produce surprisingly complex behavior.

By emphasizing clear architecture, deterministic simulation, and incremental development, the project aims to become both an educational platform for exploring emergence and a practical foundation for future experimentation.

The accompanying design documents define each subsystem in detail, while this document serves as the architectural guide connecting them into a single coherent system.