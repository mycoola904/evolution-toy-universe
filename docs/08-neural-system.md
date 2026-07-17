# Neural System

## Purpose

The neural system determines an organism's behavior by converting sensory inputs into actions. It contains no explicit goals, planning, memory, or reasoning. At each simulation tick, it evaluates the organism's current state and observations, then selects a single action to perform.

The neural system does not learn during an organism's lifetime. Its behavior is entirely determined by its genome. Over many generations, evolution may produce organisms whose neural systems exhibit increasingly effective behaviors through mutation and natural selection.

---

## Design Goals

The Version 1 neural system is intentionally simple.

Its goals are:

- Provide a deterministic mapping from sensory inputs to actions.
- Be inexpensive to evaluate each simulation tick.
- Allow behavior to evolve solely through genetic mutation.
- Be straightforward to visualize and debug.
- Provide a foundation for future evolutionary complexity.

The neural system is **not** intended to simulate biological brains or modern machine learning. It is simply a computational mechanism through which evolution can shape behavior.

---

## Overall Architecture

The Version 1 neural system consists of a single fully connected feed-forward layer.

```
Inputs
   │
   ▼
Weighted Connections
   │
   ▼
Outputs
```

Each input is connected to every output by a single weight.

There are:

- No hidden layers
- No recurrent connections
- No internal memory
- No learning during life
- No stochastic decision making

Each organism evaluates this network independently every simulation tick.

---

## Inputs

The input neurons represent information available to the organism during the current simulation tick.

Typical inputs may include:

- Current energy
- Current age
- Food present in the current cell
- Food directly ahead
- Food to the left
- Food to the right
- Neighbor ahead
- Neighbor to the left
- Neighbor to the right

The exact input set is defined by the Organism Model.

All inputs are normalized into numeric values appropriate for neural evaluation.

---

## Outputs

Each output neuron represents a possible action.

Typical outputs include:

- Move Forward
- Turn Left
- Turn Right
- Eat
- Wait
- Reproduce

Each output receives contributions from every input.

The output with the highest activation is selected as the organism's action for that simulation tick.

Only one action is performed each tick.

---

## Fully Connected Network

Every input neuron is connected to every output neuron.

For example:

```
8 Inputs

6 Outputs

Total Weights

8 × 6 = 48
```

Each organism therefore possesses exactly the same neural structure.

Only the values of the connection weights differ between organisms.

This fixed topology greatly simplifies reproduction, mutation, visualization, and debugging while still allowing a large behavioral search space for evolution.

---

## Genome Representation

The neural system is encoded directly within the organism's genome.

The genome stores every connection weight as a numeric value.

Example:

```
[
  0.81,
 -1.24,
  0.09,
 ...
]
```

The ordering of the weights is fixed and deterministic.

During reproduction, the genome is copied directly into the offspring, after which mutations may modify one or more weights.

No additional encoding or interpretation is required.

---

## Neural Evaluation

During each simulation tick the neural system performs the following steps:

1. Read the current input values.
2. Multiply each input by its corresponding connection weight.
3. Sum the weighted inputs for each output neuron.
4. Compare the output activations.
5. Select the output with the highest activation.
6. Execute the corresponding action.

This process is repeated independently for every organism during every simulation tick.

---

## Action Execution

The neural system selects an intended action but does not determine whether that action succeeds.

After the neural system chooses an action, control returns to the simulation, which evaluates the action according to the rules of the world.

For example:

- A movement action may fail if the destination cell is occupied.
- An eat action may fail if no environmental energy is available.
- A reproduction action may fail if the organism lacks sufficient energy.
- A wait action always succeeds.

The neural system receives no special knowledge about why an action succeeds or fails. It simply produces an action based on its current inputs. The simulation is solely responsible for applying the physical rules of the Toy Universe.

This separation ensures that organisms remain subject to the same universal laws as every other entity in the simulation and keeps the neural system independent of the simulation's implementation details.

---

## Activation

Version 1 uses the simplest possible activation model.

Each output activation is calculated as the weighted sum of its inputs.

```
activation = Σ(input × weight)
```

No additional activation function is applied.

Raw activation values are compared directly.

The action with the highest activation is selected.

Future versions may experiment with sigmoid, tanh, ReLU, or other activation functions if they provide meaningful advantages.

---

## Mutation

The neural system evolves through mutation of connection weights.

Possible mutations include:

- Increase a weight slightly.
- Decrease a weight slightly.
- Replace a weight with a new random value.
- Reverse the sign of a weight.

Small mutations should occur much more frequently than large mutations.

Most mutations are expected to have little or no beneficial effect. Over many generations, natural selection determines which neural configurations survive.

---

## Determinism

The neural system is entirely deterministic.

Given:

- the same genome,
- the same organism state,
- the same sensory inputs,
- and the same world state,

the organism will always produce the same action.

This determinism simplifies debugging, experimentation, and reproducibility.

Any behavioral differences between organisms arise solely from differences in their genomes or environments.

---

## Relationship to Evolution

The neural system itself never improves.

Only populations improve.

An individual organism cannot learn new behaviors during its lifetime.

Instead, successful neural configurations are passed to future generations through reproduction, while less successful configurations gradually disappear from the population.

This separation between lifetime behavior and evolutionary change is a fundamental design principle of the Toy Universe.

---

## Future Extensions

Future versions of the project may explore more sophisticated neural systems, including:

- Hidden layers
- Recurrent connections
- Short-term memory
- Long-term memory
- Dynamic neural topologies
- Evolving numbers of neurons
- Synaptic plasticity
- Hebbian learning
- Neuromodulation

These features are intentionally excluded from Version 1 in order to preserve simplicity and make the evolutionary process easier to understand.