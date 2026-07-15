# 07 – Reproduction Model

## Purpose

The Reproduction Model defines how organisms create offspring and how genetic variation enters the Toy Universe. Reproduction is the mechanism by which successful genomes persist across generations, while mutation provides the variation upon which natural selection operates.

Version 1 intentionally models only simple asexual reproduction. The objective is not to simulate biology accurately, but to provide the minimal mechanism required for evolutionary behavior to emerge.

---

# 1. Reproduction Trigger

An organism becomes eligible to reproduce when its stored energy reaches or exceeds a configurable reproduction threshold.

```
Energy >= Reproduction Threshold
```

The threshold is part of the organism's genome and may itself evolve through mutation.

Reproduction is never mandatory. If the simulation later introduces additional decision-making complexity, reproduction may become an action selected by the organism. Version 1 assumes reproduction occurs automatically whenever the threshold is reached and the remaining conditions are satisfied.

---

# 2. Space Requirement

Reproduction requires an available neighboring cell.

The simulation searches the organism's adjacent cells for an empty location in which to place the offspring.

If no suitable location exists, reproduction does not occur during that simulation tick.

This naturally limits population growth without requiring explicit population caps.

---

# 3. Energy Division

Reproduction does not create energy.

When reproduction occurs, the parent's stored energy is divided between the parent and the offspring.

Version 1 uses an equal division of energy.

```
Parent Energy = 120

↓

Parent = 60
Child  = 60
```

This preserves the conservation of energy established by the Energy Model.

---

# 4. Genome Inheritance

The offspring begins as an exact copy of the parent's genome.

```
Parent Genome

↓

Copy

↓

Child Genome
```

Only after the copy is created are mutations applied.

This guarantees that every inherited difference is the direct result of mutation.

---

# 5. Mutation

Mutation is the only source of genetic variation in Version 1.

After the offspring genome has been copied, a small mutation may be introduced.

Version 1 favors small, incremental changes rather than large random modifications. This allows evolutionary behavior to emerge gradually over many generations.

Mutations may increase or decrease a parameter's value. The simulation does not distinguish between "beneficial" and "harmful" mutations.

Whether a mutation improves survival depends entirely upon the environment in which the organism lives.

---

# 6. Mutable Traits

Any genome parameter may be subject to mutation.

Examples include:

- Reproduction threshold
- Sensor configuration
- Neural decision weights
- Behavioral parameters
- Future organism capabilities

The mutation system operates uniformly across all mutable traits. No parameter receives special treatment.

---

# 7. Natural Selection

The simulation never evaluates fitness directly.

There are no fitness scores, rankings, or reward functions.

Instead, selection emerges naturally from the interaction between organisms and their environment.

Organisms that survive long enough to reproduce pass their genomes to the next generation.

Organisms that fail to survive leave no descendants.

Evolution therefore occurs through differential survival rather than explicit optimization.

---

# 8. Lineage

Each offspring records the identity of its parent.

Maintaining parent-child relationships allows future versions of the simulation to reconstruct evolutionary histories, visualize lineages, or analyze the emergence of successful genomes.

Version 1 does not require any additional ancestry tracking beyond the immediate parent.

---

# Design Philosophy

The Reproduction Model intentionally separates inheritance from selection.

Inheritance copies information.

Mutation changes information.

The environment determines which information persists.

No mutation is inherently good or bad. The Toy Universe contains only simple physical rules. Evolution emerges from the interaction between those rules and the changing environment.