# Technical Design

## 1. Purpose

This document defines the technical design for Version 1 of the Evolution Toy Universe.

The earlier design documents describe the behavior of the universe: its simulation rules, world, organisms, energy system, reproduction, neural system, and user interface. This document describes how those designs will be organized and implemented as a Python application.

The technical design is intended to provide enough structure to begin implementation without attempting to define every class, method, or internal data structure in advance.

The primary goals of the technical design are to:

* establish the major application components,
* define clear responsibilities between components,
* preserve deterministic simulation behavior,
* keep the simulation engine independent from the user interface,
* support automated testing and repeatable experiments,
* and provide an architecture that can evolve after Version 1.

This document applies specifically to Version 1. Future versions may revise the architecture as the project grows and actual performance or usability needs become known.

---

## 2. Design Principles

The technical implementation should reflect the broader principles of the Evolution Toy Universe.

### 2.1 Simplicity First

Version 1 should use the simplest architecture that correctly implements the documented universe.

The design should avoid unnecessary abstraction, complex frameworks, speculative optimization, and features intended only for possible future requirements.

The purpose of Version 1 is to create a working universe that can be observed, tested, and experimented with.

### 2.2 Simulation Rules Are Independent of Presentation

The simulation must not depend on the user interface.

The universe should be able to run:

* with the graphical interface,
* without visualization,
* from automated tests,
* from a command-line experiment runner,
* or as part of future batch-processing tools.

The user interface may observe the simulation and submit control requests, but it must not contain or redefine simulation rules.

### 2.3 Determinism Is a Core Requirement

Given the same:

* experiment configuration,
* initial state,
* random seed,
* and software version,

the simulation should produce the same results.

Randomness must be explicit, controlled, and reproducible.

### 2.4 Model Rules Remain Authoritative

The model documents define how the Toy Universe behaves.

The technical design may determine how those rules are represented and executed, but it must not silently alter them for convenience.

When the implementation reveals ambiguity in a model rule, the ambiguity should be resolved in the appropriate design document rather than hidden inside the code.

### 2.5 Clear Code Before Fast Code

Version 1 should favor readable and testable Python code over premature optimization.

Performance should be measured before major optimization work begins. If performance later becomes limiting, the architecture should allow specific components to be optimized without redesigning the entire application.

---

## 3. Technology Stack

### 3.1 Programming Language

Python will be the primary programming language for Version 1.

Python is appropriate for the project because it supports:

* rapid development,
* readable implementation of simulation rules,
* straightforward automated testing,
* strong debugging and inspection tools,
* data analysis and visualization,
* and future performance improvements through specialized libraries if needed.

The project should target a currently supported version of Python. The exact minimum version should be recorded when implementation begins and should remain stable throughout Version 1 development unless there is a clear reason to change it.

The simulation engine and domain model should remain ordinary Python code. They
must not depend on FastAPI, browser concepts, or presentation-specific data
structures. This keeps the same simulation core available to the web
application, command-line experiments, and automated tests.

### 3.2 Dependencies

The project should prefer the Python standard library where it provides a clear and sufficient solution.

Third-party dependencies are acceptable when they provide substantial value, particularly for:

* the graphical user interface,
* testing,
* numerical processing,
* visualization,
* or data export.

Dependencies should not be introduced only to avoid writing small amounts of straightforward project code.

All dependencies should be declared in the project configuration and installed through a reproducible environment-management process.

### 3.3 Development Tools

The project should use consistent tools for:

* dependency management,
* automated testing,
* code formatting,
* linting,
* type checking where useful,
* and packaging.

The exact tools may be selected during initial project setup. Tool selection should remain lightweight and should not become a major project of its own.

### 3.4 Application and User Interface Technology

The selected application stack is:

* **FastAPI** for the web application and its HTTP and WebSocket boundaries,
* **Jinja2** for server-rendered pages and HTML fragments,
* **HTMX** for focused browser interactions without a separate single-page
  application,
* **PostgreSQL through Psycopg 3** for completed experiment persistence and
  reporting queries,
* **Plotly.js** for interactive report charts,
* **HTML Canvas** for the live two-dimensional world display,
* and a **WebSocket** connection for future live runtime snapshots and status.

FastAPI, Jinja2, and HTMX should provide experiment configuration, run
management, reports, navigation, and organism details as a server-rendered web
application. Plotly.js should receive report data prepared by the application;
it must not calculate authoritative simulation results in the browser.

The runtime grid is a specialized rendering surface within that application.
It should draw cells, energy, organisms, overlays, and animation with HTML
Canvas rather than representing every cell as an HTML element. A WebSocket may
later deliver snapshots and status for live visualization and controls without
requiring the reporting and configuration pages to become a JavaScript
application.

Selection of this stack does not require every part to be delivered in the
first UI milestone. The browser interface may begin with ordinary HTTP requests
and add the live Canvas and WebSocket runtime view when interactive simulation
work begins.

---

## 4. Architectural Overview

The application will be divided into several major responsibilities.

```text
Evolution Toy Universe
├── Simulation Engine
├── Domain Model
├── Experiment Configuration
├── Metrics and History
├── Persistence and Export
├── User Interface
└── Application Entry Points
```

These are logical responsibilities. They do not necessarily require one package or class for each item.

### 4.1 Simulation Engine

The simulation engine coordinates the execution of the universe.

It is responsible for:

* maintaining the current tick,
* controlling the simulation-owned random-number generator,
* executing simulation phases in the documented order,
* collecting organism intentions,
* resolving conflicting actions,
* applying state changes,
* performing reproduction and death checks,
* updating the environment,
* and requesting metrics collection.

The engine should coordinate behavior rather than contain every model rule itself.

### 4.2 Domain Model

The domain model represents the state of the Toy Universe.

Its major concepts include:

* universe state,
* world grid,
* cells,
* environmental energy,
* organisms,
* genomes,
* neural networks,
* actions,
* and experiment state.

The domain model should contain the data and behavior needed to represent these concepts without depending on the user interface.

### 4.3 Experiment Configuration

Experiment configuration defines the initial conditions and permitted configurable values for a simulation run.

It is responsible for:

* validating experiment settings,
* creating the initial world,
* creating the initial organisms,
* establishing the random seed,
* and recording the settings needed to reproduce the run.

### 4.4 Metrics and History

The metrics system observes simulation results without affecting them.

It is responsible for collecting and summarizing values such as:

* population,
* births,
* deaths,
* organism energy,
* environmental energy,
* age,
* reproduction,
* mutations,
* and extinction.

Metrics should remain separate from the rules that determine organism or environmental behavior.

### 4.5 Persistence and Export

Persistence is responsible for saving information produced by the simulation.

Version 1 may support:

* experiment configuration files,
* run summaries,
* metrics history,
* selected snapshots,
* and exported organism or genome data.

Full save-and-resume support is not assumed unless it is explicitly selected as a Version 1 requirement.

### 4.6 User Interface

The user interface is responsible for:

* displaying the world,
* displaying metrics,
* accepting experiment configuration,
* controlling execution,
* selecting organisms,
* and presenting organism details.

The interface observes simulation state but does not directly implement simulation rules.

### 4.7 Application Entry Points

The project should support more than one way to start a simulation.

Likely entry points include:

* an interactive graphical application,
* a command-line experiment runner,
* and automated tests.

These entry points should construct and use the same simulation engine.

---

## 5. Proposed Project Structure

The exact filenames may evolve during implementation, but the project should begin with a clear separation of responsibilities.

A possible structure is:

```text
evolution-toy-universe/
├── docs/
├── src/
│   └── evolution_toy_universe/
│       ├── domain/
│       ├── simulation/
│       ├── experiments/
│       ├── metrics/
│       ├── persistence/
│       ├── ui/
│       └── application/
├── tests/
├── pyproject.toml
└── README.md
```

### 5.1 `domain`

The `domain` package should contain the core representations of the universe.

Possible responsibilities include:

* positions and directions,
* cells and the world grid,
* organisms,
* genomes,
* neural networks,
* actions,
* and shared domain values.

The package name does not imply that every concept must be implemented as a class.

### 5.2 `simulation`

The `simulation` package should coordinate the simulation loop and its phases.

Possible responsibilities include:

* simulation state,
* perception,
* neural evaluation,
* intention collection,
* conflict resolution,
* action application,
* energy accounting,
* reproduction,
* death,
* and environmental updates.

### 5.3 `experiments`

The `experiments` package should manage:

* configuration definitions,
* validation,
* initial-state construction,
* random seeds,
* stopping conditions,
* and experiment execution.

### 5.4 `metrics`

The `metrics` package should contain:

* metric collection,
* history records,
* run summaries,
* and derived statistics.

### 5.5 `persistence`

The `persistence` package should contain:

* configuration loading and saving,
* result export,
* snapshot serialization if supported,
* and validation of loaded data.

### 5.6 `ui`

The `ui` package should contain all framework-specific user-interface code.

The simulation and domain packages must not import from the UI package.

### 5.7 `application`

The `application` package should connect the major components.

It may provide:

* graphical application startup,
* command-line startup,
* dependency construction,
* and coordination between the UI and simulation engine.

### 5.8 `tests`

Tests should generally mirror the application structure.

The test suite should include:

* focused rule tests,
* simulation-phase tests,
* deterministic replay tests,
* invariant tests,
* and small end-to-end simulations.

---

## 6. Core Domain Representation

The implementation should clearly define which component owns each part of the universe state.

### 6.1 Simulation State

The simulation state represents the complete state required to continue a run.

It should include or reference:

* the current tick,
* the world,
* all living organisms,
* experiment configuration,
* random-number state,
* metrics state where necessary,
* and run status.

The state should not include UI-specific values such as zoom level, selected overlays, window size, or currently selected organism.

### 6.2 World

The world owns the two-dimensional toroidal grid described in `04-world-model.md`.

The world is responsible for representing:

* grid dimensions,
* cells,
* environmental energy,
* organism occupancy,
* and coordinate wrapping.

The world should provide clear operations for querying positions and neighboring cells.

Coordinate wrapping should be implemented in one shared location rather than duplicated throughout the code.

### 6.3 Cells

A cell represents one location in the world.

For Version 1, a cell contains:

* environmental energy,
* and zero or one organism occupant.

A cell should not independently decide when to regenerate energy, transfer energy, or update its occupant. Those changes are coordinated by the simulation engine according to the documented update order.

### 6.4 Organisms

An organism represents a living entity in the universe.

Each organism should have a stable unique identifier for the duration of the run.

Its state includes:

* position,
* orientation,
* stored energy,
* age,
* genome,
* neural-system state where required,
* and lineage information selected for Version 1.

An organism should not have direct access to the complete mutable world state when choosing an action.

Instead, the simulation should provide the organism or neural system with the sensor values defined by the organism model.

### 6.5 Genome

The genome contains the inherited values that define the organism’s neural system and other evolvable traits defined by the model documents.

The genome should be treated as a distinct concept from the organism.

This separation supports:

* inheritance,
* mutation,
* comparison between organisms,
* lineage analysis,
* and testing.

A child should receive a newly created genome based on the parent genome and the reproduction rules. The child should not share a mutable genome object with the parent.

### 6.6 Neural System

The neural system converts sensor inputs into action output values according to `08-neural-system.md`.

The implementation should preserve a clear distinction between:

* the genome values that define the network,
* the temporary input and output values calculated during a tick,
* and the final action selected from those outputs.

The neural-system implementation should not query the world directly.

### 6.7 Actions and Intentions

An action represents one of the permitted organism behaviors defined by the simulation and organism models.

Examples include:

* move,
* turn,
* consume,
* and wait.

During a tick, an organism produces an intended action.

An intention should contain all information required for later resolution, such as:

* organism identifier,
* selected action,
* target position where applicable,
* and any other action parameters.

Creating an intention must not immediately modify the universe.

### 6.8 Experiment Configuration

Experiment configuration should be represented as a validated, explicit object rather than as unrelated global constants.

It should contain the settings that may vary between experiments.

Model rules that are fixed for Version 1 should remain code-level or model-level constants unless the design explicitly identifies them as experiment settings.

This distinction prevents every implementation value from becoming user-configurable.

---

## 7. Simulation Engine

The simulation engine implements the synchronous tick process defined in `03-simulation-model.md`.

The engine should expose a small and clear set of operations, such as:

* initialize a run,
* execute one tick,
* execute multiple ticks,
* pause,
* resume,
* stop,
* and inspect current state.

The exact method names are implementation details and are not defined here.

### 7.1 Tick Orchestration

One component should be responsible for coordinating the entire tick.

A tick should proceed through explicit phases rather than allowing organisms, cells, and subsystems to update themselves independently.

A conceptual flow is:

```text
Begin Tick
    ↓
Capture Starting State
    ↓
Perception
    ↓
Neural Evaluation
    ↓
Action Selection
    ↓
Collect Intentions
    ↓
Resolve Conflicts
    ↓
Apply Actions
    ↓
Energy Accounting
    ↓
Reproduction and Death
    ↓
Environment Update
    ↓
Metrics Collection
    ↓
Advance Tick
```

The exact ordering must match the authoritative simulation model.

If the model document changes, this flow must be updated accordingly.

### 7.2 Starting-State Consistency

All organisms should perceive the same logical starting state for a tick.

An organism earlier in the iteration order must not receive an advantage because another organism has already moved or consumed energy during that same tick.

This requirement may be implemented through:

* an immutable snapshot,
* controlled read-only access to the current state,
* staged writes,
* or another design that provides equivalent behavior.

A complete deep copy of the universe is not required if the same guarantees can be achieved more efficiently.

### 7.3 Perception

During perception, the simulation produces the sensor inputs defined in `05-organism-model.md`.

Perception should:

* read from the tick’s starting state,
* use shared coordinate and direction logic,
* produce sensor values in a consistent order,
* and avoid uncontrolled randomness.

The sensor values should be inspectable for debugging and organism analysis.

### 7.4 Neural Evaluation and Action Selection

Each organism’s sensor values are passed to its neural system.

The neural system calculates output values, and the action-selection rule chooses the organism’s intended action.

Tie-breaking rules must be deterministic unless the model explicitly requires randomness.

If random tie-breaking is permitted, it must use the simulation-owned random-number generator.

### 7.5 Intention Collection

All organism intentions are collected before any organism action is applied.

This preserves synchronous behavior and makes conflict resolution explicit.

Intention collection should not modify:

* organism positions,
* cell occupancy,
* environmental energy,
* organism energy,
* or organism existence.

### 7.6 Conflict Resolution

Conflicts occur when multiple intentions cannot all be completed.

Examples may include:

* multiple organisms attempting to enter the same cell,
* an organism attempting to enter a cell whose occupant is not leaving,
* or multiple actions targeting a limited resource.

Conflict-resolution rules are part of the simulation model and must be applied consistently.

Resolution should not accidentally depend on:

* dictionary ordering,
* memory location,
* object creation order,
* UI selection,
* or operating-system scheduling.

When a deterministic ordering is required, a stable value such as organism identifier may be used only if that behavior is consistent with the documented model.

When randomness is required, it must come from the simulation-owned random-number generator.

### 7.7 Action Application

After intentions have been resolved, approved results are applied to the universe.

Action application should occur through controlled state-changing operations.

This reduces the risk of:

* two organisms occupying the same cell,
* organism position disagreeing with cell occupancy,
* energy being transferred twice,
* or an organism acting after it has been removed.

### 7.8 Energy Accounting

Energy changes should follow `06-energy-model.md`.

The implementation should make energy transfers explicit and testable.

Where possible, an energy transfer should identify:

* the source,
* the destination,
* the amount,
* and the reason.

The three energy conservation laws defined in the energy model should be treated as implementation invariants and test targets.

Action costs, consumption, reproduction transfers, and environmental regeneration must be applied in the documented phases.

### 7.9 Reproduction and Death

Reproduction and death checks should follow the order defined in the simulation and reproduction documents.

Reproduction should:

* identify eligible organisms,
* create the child genome,
* apply mutation,
* allocate parent and child energy,
* find or validate the child position,
* create the child organism,
* and update occupancy consistently.

Death should remove the organism from:

* the organism collection,
* the world occupancy state,
* and any active indexes.

Metrics or history may retain a record of the organism after its removal from the living universe.

### 7.10 Environmental Update

Environmental updates should be coordinated by the simulation engine rather than performed independently by cells.

For Version 1, the environmental update occurs after organism actions,
reproduction, and death processing. The engine samples
`regeneration_cell_count` distinct cell indexes through the simulation-owned
seeded random-number generator, then attempts to add `regeneration_amount` to
each selected cell. Sampling without replacement makes every selected cell
unique within the tick.

Actual energy added to a cell is limited by `maximum_cell_energy`; excess
attempted energy is recorded as wasted and is not redirected. If either the
cell count or amount is zero, the phase performs no selection and consumes no
random values. Metrics distinguish attempted input, actual input, and input
wasted at the cap.

The implementation should ensure that environmental energy:

* remains within permitted bounds,
* changes at the documented time,
* and is not created or removed outside the defined rules.

### 7.11 Metrics Collection

Metrics should be collected after the tick reaches a defined completed state.

The metrics system should read simulation state without changing it.

The precise collection point should remain consistent so that a metric labeled for a particular tick always represents the same phase boundary.

---

## 8. Determinism, Randomness, and Invariants

### 8.1 Simulation-Owned Randomness

Each experiment should create an explicit random-number generator from the experiment seed.

All simulation randomness must use this generator.

Simulation code should not use uncontrolled global random functions.

Potential uses of controlled randomness include:

* initial organism placement,
* initial genome generation,
* mutation,
* randomized conflict resolution where specified,
* and other rules explicitly defined as random.

### 8.2 Random-Call Stability

Determinism depends not only on the seed but also on the order in which random values are requested.

The implementation should avoid unnecessary random calls and should keep random behavior localized and testable.

Changes to random-call order may change the full outcome of a run even when the model rules appear unchanged. Such changes should therefore be treated as behaviorally significant.

### 8.3 Stable Iteration

Simulation results should not depend on accidental collection ordering.

Any iteration order that affects behavior should be explicitly defined.

Where order should not matter, tests should be designed to detect accidental ordering dependence.

### 8.4 Reproducibility Record

Each saved run summary should include enough information to reproduce the experiment.

At minimum, this should include:

* software or model version,
* experiment configuration,
* random seed,
* stopping condition,
* and relevant execution options.

### 8.5 Domain Invariants

The simulation should enforce important invariants.

Examples include:

* each living organism occupies exactly one cell,
* no cell contains more than one organism,
* an organism’s recorded position matches its occupied cell,
* all living-organism identifiers are unique,
* environmental energy remains within valid limits,
* organism energy uses valid numeric values,
* genome dimensions match neural-system dimensions,
* and the total energy behavior follows the energy model.

Invariant checks may run frequently during tests and optionally during development runs.

They may be reduced or disabled in performance-sensitive production runs only after the system is well tested.

Unexpected invariant violations should fail clearly. They should not be silently repaired.

---

## 9. Experiment Configuration

Experiment configuration defines the permitted starting conditions and run controls for a simulation.

Likely Version 1 configuration values include:

* world width and height,
* initial organism count,
* initial environmental energy distribution,
* environmental regeneration cell count,
* environmental regeneration amount,
* organism starting energy,
* action energy costs,
* reproduction threshold,
* mutation probability,
* mutation magnitude,
* neural-system dimensions,
* random seed,
* maximum tick count,
* and stopping conditions.

The final list must match the settings approved in the model and UI documents.

### 9.1 Fixed Rules Versus Experiment Settings

Not every value in the implementation should be configurable.

A value should be an experiment setting when changing it is an intentional part of running a different experiment.

A value should remain fixed when it defines the Version 1 model itself.

For example, a reproduction threshold may be an experiment setting, while the fact that reproduction occurs through division may remain a fixed model rule.

This distinction should be documented alongside the configuration definition.

### 9.2 Validation

Configuration must be validated before a simulation begins.

Validation should reject values such as:

* nonpositive world dimensions,
* more initial organisms than available cells,
* negative energy values where not permitted,
* a regeneration cell count that is negative or exceeds world capacity,
* a negative or non-finite regeneration amount,
* invalid mutation probabilities,
* incompatible neural dimensions,
* and invalid stopping conditions.

Validation errors should clearly identify the setting and the reason it is invalid.

### 9.3 Initial-State Construction

Initial-state construction should be centralized.

Given a validated configuration and random seed, it should create:

* the world,
* environmental energy,
* initial organisms,
* initial genomes,
* positions,
* orientations,
* and the initial simulation state.

This process must be deterministic.

### 9.4 Stopping Conditions

A run may stop because of:

* reaching a configured maximum tick,
* extinction of all organisms,
* a user stop request,
* an unrecoverable error,
* or another explicitly configured condition.

The final run status should record why the simulation ended.

---

## 10. Metrics, History, and Diagnostics

### 10.1 Version 1 Metrics

The metrics system should initially focus on measurements that help determine whether the universe is behaving correctly and interestingly.

Possible metrics include:

* current population,
* births per tick,
* deaths per tick,
* cumulative births and deaths,
* average organism age,
* maximum organism age,
* average organism energy,
* minimum and maximum organism energy,
* total organism energy,
* total environmental energy,
* reproduction count,
* mutation count,
* and extinction tick.

Additional metrics should be added only when they answer a clear question.

### 10.2 History Records

Metrics may be recorded every tick or at a configurable interval.

Recording every tick is simplest and most detailed but may use substantial memory during long runs.

Version 1 should support a clear history-retention policy, such as:

* retain every tick for short experiments,
* retain periodic summaries for long experiments,
* export history while the simulation runs,
* or limit retained in-memory history.

The initial implementation may begin with full per-tick history for manageable Version 1 run sizes.

### 10.3 Snapshots

A snapshot represents the state of the universe at a particular tick.

Snapshots may support:

* UI rendering,
* organism inspection,
* debugging,
* export,
* and future replay features.

The UI should receive a safe representation of state rather than unrestricted access to mutable simulation internals.

A snapshot does not necessarily need to contain every implementation detail.

### 10.4 Organism Inspection

The diagnostic system should support inspection of an organism’s:

* identifier,
* age,
* energy,
* position,
* orientation,
* genome,
* sensor inputs,
* neural outputs,
* selected action,
* parent or lineage information where retained,
* and recent state where practical.

This inspection supports the UI goal of comparing successful and unsuccessful organisms.

Detailed tracing should be optional because tracing every organism on every tick could produce excessive data.

### 10.5 Logging

Application logging should include enough information to diagnose failures without overwhelming normal use.

Useful logged events may include:

* experiment start,
* configuration and seed,
* experiment stop reason,
* invariant failures,
* persistence errors,
* UI or simulation exceptions,
* and optional performance measurements.

Routine organism actions should not be logged individually unless detailed tracing is enabled.

---

## 11. Persistence and Data Formats

Version 1 uses PostgreSQL through Psycopg 3. PostgreSQL records completed
experiments; it is not the source of live simulation state and is never
accessed by domain classes.

The application boundary converts a completed simulation into plain result
snapshots and passes them to the persistence layer. Saving one run and all of
its organism results occurs in one PostgreSQL transaction so a failure cannot
leave a partial experiment.

### 11.1 Run Provenance and Configuration

Each run stores its seed, world dimensions, population counts, completed tick,
termination reason, UTC start time, Git commit, Git dirty state, and complete
validated configuration as JSONB. Git fields are nullable when provenance
cannot be obtained; an unknown state is not treated as clean. Start times use
timezone-aware PostgreSQL timestamps and Git dirty state uses a native nullable
boolean.

New runs also store the completed structured aggregate report in nullable JSONB
`report_json`. This is a presentation-neutral snapshot used by both the CLI
formatter and web renderer. Null identifies a legacy run whose normalized data
is still valid but whose non-normalized historical aggregates were not stored.

### 11.2 Organism Results

Every organism created during a run receives one lifetime result. Results
include the run-local organism and parent IDs, birth and death ticks, lifespan,
initial/final/peak energy, environmental energy consumed, movement distance,
genome JSON, and the number of neural weights that actually changed when a
child was born. Initial organisms use a null mutation count, while a child with
no changed weights uses zero. Whether a child received a mutation is derived
from whether this count is positive. Dead organisms remain available through
their metrics records after being removed from the living population.

Per-tick and cell-by-cell persistence are intentionally excluded from Version
1. Derived leaderboards and summaries should be calculated with SQL rather than
duplicated in summary tables.

### 11.3 Command-Line Behavior

Normal command-line runs persist automatically using the connection string in
`DATABASE_URL`. Application startup and pytest load a repository-root `.env`
file through `python-dotenv` without overriding variables already present in the
process environment. Connection strings are not accepted as command-line
arguments so credentials are not placed in shell history or process listings.
`--no-persist` disables connection configuration, database work, and
Git-provenance work. Connection, migration, and write failures are fatal.

### 11.4 Verification Queries

Recent runs can be inspected with:

```sql
SELECT id, started_at, seed, ticks_completed, termination_reason,
       git_commit, git_dirty
FROM simulation_runs
ORDER BY id DESC
LIMIT 10;
```

Organism leaderboards can be calculated directly from lifetime results:

```sql
SELECT simulation_run_id, organism_id, lifespan,
       energy_consumed, distance_moved, peak_energy
FROM organism_results
ORDER BY lifespan DESC
LIMIT 10;
```

### 11.5 Universe Save and Resume

Full save-and-resume support may require serialization of:

* the complete world,
* every organism,
* every genome,
* current tick,
* random-number state,
* configuration,
* and relevant runtime state.

This capability would be useful but adds complexity.

Unless a strong Version 1 need is identified, the initial implementation may support saved configuration and results without supporting continuation of an interrupted run.

The architecture should not intentionally prevent save-and-resume from being added later.

### 11.6 Data Versioning

Schema changes are stored as consecutively numbered SQL files and tracked in
`schema_migrations` with their names, checksums, and application timestamps.
Initialization acquires a transaction-scoped PostgreSQL advisory lock, validates
the complete applied history, and applies pending migrations transactionally.
Unknown versions, history gaps, and changed checksums are rejected with a clear
compatibility error.

PostgreSQL migration numbering begins at `001` and is independent of the former
SQLite `PRAGMA user_version`. Historical SQLite experiment data is not imported.

---

## 12. User Interface Integration

The user interface described in `09-ui.md` is a passive visualization and control layer over the simulation.

```text
Browser
├── Jinja2 pages and HTMX fragments
├── Plotly.js report charts
└── Canvas runtime view
        │
        │ future live snapshots and status over WebSocket
        v
FastAPI application
├── experiment and run coordination
├── reporting queries
└── snapshot and inspection boundaries
        │
        ├── Python simulation core
        └── PostgreSQL through Psycopg 3
```

FastAPI is an application boundary, not part of the universe model. HTTP
requests, HTMX events, WebSocket messages, rendering cadence, and browser state
must not determine simulation rules or outcomes.

### 12.1 Simulation Control

The UI should support:

* create experiment,
* start,
* pause,
* resume,
* stop,
* reset,
* and single-tick advancement where useful.

Pause should stop additional ticks from beginning. It should not leave the simulation halfway through a tick.

### 12.2 Rendering

The UI should render a stable snapshot of the universe.

It should not read mutable simulation structures while a tick is changing them.

The rendering system should display:

* cells,
* environmental energy,
* organisms,
* organism orientation where selected,
* overlays,
* and basic experiment status.

The live world should be rendered with HTML Canvas. Jinja2 should render the
page containing the Canvas and its surrounding controls, while HTMX should
handle page- or panel-level interactions that benefit from server-rendered HTML.
Canvas drawing code may interpolate visual movement, show effects, or retain
short-lived trails, but those display choices must not feed back into the
simulation.

Plotly.js should be used for report and history charts rather than for the live
world grid. Chart inputs should come from application reporting queries or
simulation snapshots through explicit serialization boundaries.

### 12.3 Simulation Rate and Display Rate

Simulation speed and rendering speed should be separate concepts.

The simulation may execute:

* one tick per display update,
* multiple ticks per display update,
* or run without display updates.

This separation allows faster experiments and prevents graphical performance from defining simulation performance.

### 12.4 UI Responsiveness

Long-running simulation work should not freeze the interface.

FastAPI request handlers must not run a long simulation inline. The
implementation may use:

* a worker thread,
* a worker process,
* a timer-driven step loop,
* message passing,
* or another safe coordination mechanism.

Concurrency must not change simulation behavior.

Only the simulation engine should modify simulation state.

A future WebSocket endpoint may publish immutable snapshots, metrics, and run
status to the Canvas view and receive control commands. The transport must not
expose mutable domain objects or make simulation progress depend on whether a
browser is connected.

### 12.5 Commands and Snapshots

Communication between the UI and engine should use clear boundaries.

The UI sends commands such as:

* start,
* pause,
* stop,
* step,
* reset,
* or select configuration.

The engine provides:

* current status,
* metrics,
* snapshots,
* and inspection data.

The UI should not modify cells, organisms, genomes, or energy directly.

### 12.6 Organism Selection

Selecting an organism in the UI should identify it through its stable organism identifier.

If the selected organism dies, the UI should handle that state clearly rather than accidentally displaying another organism that later occupies the same position.

### 12.7 Experiment Configuration UI

The experiment-configuration screen should construct the same validated configuration object used by command-line and test entry points.

The UI should not maintain a separate interpretation of valid experiment settings.

### 12.8 Experiment Console V1

The first browser milestone provides server-rendered experiment setup, completed
run detail, run history, predefined PostgreSQL reports, and saved-run
comparison. The CLI and FastAPI entry points both call the reusable experiment
runner, which owns the simulation loop and completed-result persistence. Route
handlers do not duplicate domain execution rules.

The setup page exposes seed, maximum ticks, world dimensions, initial population
and organism energy, regeneration cell count and amount, reproduction threshold,
and mutation rate and amount. Presets are application constants that populate
the editable form; `simulation_runs.config_json` remains the authoritative
record of submitted configuration.

For this milestone, an HTTP submission waits for completion while the runner is
executed in a server worker thread so the event loop remains responsive. This
is an intentionally limited synchronous workflow. Long-running and concurrent
operation should replace that adapter with process-based/background
coordination without changing the experiment runner's simulation behavior.

Run detail includes a Plotly.js organism-lifespan distribution prepared from
reporting-query output. It supports raw count and run-normalized percentage and
separates organisms alive at completion from organisms that died. Tables remain
the primary reporting interface. The live Canvas grid and WebSocket
snapshot/control boundary remain deferred.

### 12.9 Structured Reports and Lineage Analysis

Completed simulation state is converted once into an immutable structured
experiment report containing the same aggregates used by terminal and browser
formatters. Report construction is observational and must not advance the
simulation or consume random values. The persistence boundary serializes this
aggregate report to `simulation_runs.report_json`; normalized run and organism
rows remain authoritative and the report JSON does not duplicate organism rows.
The column is nullable so runs from before this migration continue to load with
their normalized summaries, though historical aggregates that were never
stored cannot be reconstructed exactly.

Lineage analysis reads normalized organism results and reconstructs families in
application reporting code. A founder has no parent and was born at tick zero.
The founder is generation zero, `generations_reached` is maximum descendant
depth, and a family survives when at least one member has no death tick at run
completion. Family summaries and immutable tree nodes are prepared before the
template boundary; route functions and Jinja templates do not implement
recursive lineage calculations.

Organism inspection also reads the normalized `organism_results` rows rather
than copying genomes into `report_json`. A presentation-neutral inspection
helper resolves founder and generation context, parent/sibling/child links, and
compares the child's persisted genome with its persisted parent genome. It
returns both full genomes and structured differences with parent value, child value, and
numeric delta. The calculated difference count is checked against
`mutated_weight_count`; disagreement or malformed topology is surfaced as
diagnostic information instead of breaking the page. Founder and unchanged
descendant states are represented explicitly.

---

## 13. Error Handling and Validation

Errors should be classified so that the application can respond appropriately.

### 13.1 Configuration Errors

Configuration errors occur before the simulation begins.

They should be presented clearly to the user and should not create a partial simulation.

### 13.2 Domain or Invariant Errors

Domain errors indicate that the universe has entered an invalid state.

Examples include:

* conflicting occupancy,
* missing organism references,
* invalid energy values,
* or incompatible genome dimensions.

These errors should stop the run and preserve as much diagnostic information as possible.

### 13.3 Persistence Errors

Persistence errors may include:

* unreadable files,
* invalid data,
* unsupported versions,
* missing required fields,
* or failed writes.

The application should avoid partially overwriting valid existing data.

### 13.4 User Interface Errors

UI errors should not silently corrupt simulation state.

Where possible, the current experiment state should remain valid even if rendering or a secondary display feature fails.

### 13.5 Unexpected Exceptions

Unexpected exceptions should:

* stop the active run safely,
* record the tick and experiment information,
* preserve the exception details,
* and provide a clear error message.

The application should not automatically continue after an unknown simulation exception.

---

## 14. Testing Strategy

Automated testing is essential because the universe contains many interacting rules whose failures may not be visually obvious.

### 14.1 Unit Tests

Unit tests should cover focused behavior such as:

* coordinate wrapping,
* direction changes,
* sensor calculations,
* neural calculations,
* action selection,
* mutation,
* energy transfers,
* reproduction eligibility,
* and configuration validation.

### 14.2 Simulation-Phase Tests

Each simulation phase should be testable with a small controlled universe.

Examples include:

* multiple organisms perceiving the same starting state,
* intentions being collected without mutation,
* movement conflicts being resolved correctly,
* energy being charged at the correct phase,
* and environmental updates occurring at the correct time.

### 14.3 Deterministic Replay Tests

A deterministic replay test should run the same experiment more than once and verify that the results are identical.

Comparison may include:

* final world state,
* organism states,
* genome values,
* metrics history,
* and stop reason.

### 14.4 Energy Tests

The energy conservation laws should have explicit automated tests.

Tests should examine:

* action costs,
* environmental consumption,
* reproduction transfers,
* environmental regeneration,
* death,
* and total energy accounting.

### 14.5 Reproduction and Mutation Tests

Tests should verify:

* reproduction threshold behavior,
* parent and child energy allocation,
* child placement,
* genome copying,
* mutation probability,
* mutation bounds,
* and absence of shared mutable genome state.

### 14.6 Conflict-Resolution Tests

Conflict tests should cover all documented conflict cases.

They should also verify that results do not depend on accidental iteration order.

### 14.7 Invariant Tests

Small simulations should check all major invariants after every tick.

Property-based or randomized tests may later be useful for exploring combinations that were not anticipated in hand-written examples.

### 14.8 End-to-End Tests

End-to-end tests should run small experiments from configuration through completion.

These tests should verify that:

* initialization succeeds,
* ticks execute,
* metrics are collected,
* stopping conditions work,
* and results can be exported.

### 14.9 User Interface Tests

UI tests should focus on important boundaries:

* controls send correct commands,
* snapshots render without changing simulation state,
* invalid configurations are rejected,
* and organism selection remains tied to stable identifiers.

The core simulation should not require UI tests to establish correctness.

---

## 15. Performance Approach

Version 1 performance work should follow measurement rather than assumption.

### 15.1 Initial Approach

The initial implementation should use:

* clear Python,
* straightforward domain objects,
* reasonable collections,
* explicit simulation phases,
* and simple algorithms.

The first performance goal is to support a useful Version 1 world size at an understandable speed.

### 15.2 Rendering Separation

Rendering should not occur after every tick unless the selected display rate requires it.

Headless experiments should avoid all graphical work.

### 15.3 Profiling

When performance becomes a concern, the application should be profiled to identify actual bottlenecks.

Likely areas may include:

* sensor calculation,
* neural evaluation,
* world-neighbor queries,
* action conflict resolution,
* snapshots,
* or metrics history.

No component should be rewritten solely because it appears theoretically expensive.

### 15.4 Possible Optimization Paths

If profiling identifies a genuine need, possible improvements include:

* reducing unnecessary allocations,
* improving indexing,
* caching safe calculations,
* using more compact representations,
* batching numerical work,
* using NumPy,
* using compiled Python extensions,
* or replacing a bounded simulation component with a compiled implementation.

These are future options, not Version 1 requirements.

### 15.5 Architectural Boundary

The simulation engine should have clear enough boundaries that a future high-performance implementation could replace or accelerate part of it without requiring a complete rewrite of:

* the UI,
* experiment configuration,
* persistence,
* or metrics analysis.

Cross-language replacement is not currently planned.

---

## 16. Version 1 Execution and Distribution

Version 1 is expected to run as a local Python application.

### 16.1 Development Execution

Developers should be able to:

* create an isolated Python environment,
* install declared dependencies,
* run automated tests,
* launch the UI,
* and run a headless experiment.

### 16.2 Command-Line Runner

A command-line runner should support at least:

* selecting a configuration file,
* overriding or providing a seed,
* running without the UI,
* and writing results to an output location.

The exact command syntax will be defined during implementation.

### 16.3 Graphical Application

The graphical application should provide a simple launch path suitable for local use.

Packaging into a standalone executable may be considered later but is not required to begin Version 1 development.

### 16.4 Supported Platforms

The primary development and Version 1 execution environment will be documented when implementation begins.

Cross-platform support is desirable where it comes naturally from Python and
the selected web stack, but it should not delay the first working release.

### 16.5 Output Organization

Experiment outputs should use a predictable directory structure.

A run directory may contain:

* the validated configuration,
* run metadata,
* metrics history,
* summary results,
* logs,
* and selected snapshots or exports.

Each run should have a unique identifier or directory name to avoid accidental overwriting.

---

## 17. Deferred Technical Features

The following features are intentionally deferred unless they become necessary during Version 1 development:

* distributed simulation,
* cloud execution,
* networked or multiplayer access,
* GPU processing,
* a database-backed experiment repository,
* plugin architecture,
* scripting extensions,
* user accounts,
* remote control,
* live collaboration,
* full historical replay,
* advanced lineage visualization,
* automatic parameter search,
* machine-learning frameworks,
* and a compiled simulation engine.

Deferral does not mean these features are rejected permanently.

They are excluded so that Version 1 can focus on implementing and observing the universe already defined.

---

## 18. Open Technical Questions

The following questions should be resolved before or during early implementation.

### 18.1 Runtime Execution Model

How should FastAPI coordinate a long-running interactive simulation without
blocking request handling?

The first implementation should choose the simplest safe worker model that:

* preserves deterministic single-owner updates,
* accepts control commands at clear tick boundaries,
* publishes immutable snapshots for HTTP and WebSocket consumers,
* handles cancellation and application shutdown cleanly,
* and does not require a separate distributed job system before it is needed.

### 18.2 Domain Mutability

Should the universe use primarily mutable domain objects with controlled updates, immutable state records that produce a next state, or a hybrid approach?

The selected approach must preserve synchronous updates without making the implementation unnecessarily expensive or complex.

### 18.3 World Storage

Should the grid be represented as:

* nested Python collections,
* a flat indexed collection,
* a specialized numerical array,
* or another structure?

The first implementation should prioritize clarity while supporting efficient neighbor access and occupancy updates.

### 18.4 Organism Collection and Indexes

How should organisms be stored and retrieved efficiently by:

* identifier,
* position,
* and iteration order?

The design must avoid conflicting sources of truth between the world and organism collection.

### 18.5 Snapshot Representation

What state should be included in UI and persistence snapshots?

Snapshots must be safe to inspect without allowing external mutation of the active simulation.

### 18.6 History Retention

How many ticks of detailed history should remain in memory?

Should Version 1:

* retain all history,
* retain a fixed window,
* record periodic summaries,
* or stream results to disk?

### 18.7 Save and Resume

Does Version 1 require full save-and-resume capability, or are reproducible configuration files and exported results sufficient?

### 18.8 Initial Version 1 Scale

What world dimensions, organism counts, and run lengths define acceptable initial performance?

A concrete target will help guide implementation and later profiling.

### 18.9 Lineage Data

How much parent and ancestry information should be retained for each organism?

The minimum may be a parent identifier and generation number. More complete ancestry tracking may significantly increase retained data.

### 18.10 Model Version Identification

How should saved experiments identify the exact model and software version required for reproducibility?

---

## 19. Version 1 Technical Direction

Version 1 will be implemented as a deterministic Python application with a simulation engine that is independent of the user interface.

The application will:

* represent the universe through explicit domain objects and state,
* execute each tick through controlled phases,
* collect intentions before applying actions,
* centralize randomness under a recorded seed,
* validate important invariants,
* support both graphical and headless execution,
* collect metrics without influencing the universe,
* save reproducible configurations and experiment results,
* and favor understandable code over premature optimization.

The initial architecture should be strong enough to guide development but simple enough to change when implementation reveals a better design.

The purpose of the technical design is not to predict every class or function.

Its purpose is to establish a reliable foundation from which the first working Evolution Toy Universe can be built, observed, tested, and allowed to evolve.
