import random

from domain.world import World
from domain.simulation_config import SimulationConfig
from domain.cell import Cell
from domain.organism import Organism
from domain.genome import Genome
from domain.neural_network import NeuralNetwork
from domain.direction import Direction
from domain.action import Action
from domain.sensor import Sensor
from domain.simulation_metrics import (
    EnvironmentalRegenerationResult,
    OrganismMetrics,
    SimulationMetrics,
    TickMetrics,
    new_action_counts,
)

class Simulation:
    def __init__(
        self,
        world: World,
        config: SimulationConfig,
    ):
        self.initial_world_energy = 0.0
        self.config = config
        self.random = random.Random(config.seed)
        self.world = world
        self.tick = 0
        self.organisms: list[Organism] = []
        self.next_organism_id = 0
        self.metrics = SimulationMetrics(
            organism_metrics={},
            tick_history=[],
            action_counts=new_action_counts(),
        )


    @classmethod
    def big_bang(
        cls,
        config: SimulationConfig,
    ) -> "Simulation":
        cells = [
            Cell()
            for _ in range(
                config.world_width * config.world_height
            )
        ]

        world = World(
            width=config.world_width,
            height=config.world_height,
            cells=cells,
        )

        simulation = cls(
            world=world,
            config=config,
        )

        simulation.initialize_cell_energy(
            minimum_energy=config.minimum_cell_energy,
            maximum_energy=config.maximum_cell_energy,
        )

        simulation.initial_world_energy = (
            simulation.total_world_energy()
        )

        for _ in range(config.initial_organisms):
            simulation.create_initial_organism(
                energy=config.initial_organism_energy,
                minimum_weight=config.minimum_initial_weight,
                maximum_weight=config.maximum_initial_weight,
            )

        simulation.metrics.peak_population = len(
            simulation.organisms
        )

        return simulation

    def initialize_cell_energy(
        self, 
        minimum_energy: int,
        maximum_energy: int
    ) -> None:
        for cell in self.world.cells:
            cell.energy = self.random.randint(
                minimum_energy, 
                maximum_energy
                )

    def total_world_energy(self) -> float:
        return sum(
            cell.energy 
            for cell in self.world.cells
            ) 
    
    def random_position(self) -> tuple[int, int]:
        x = self.random.randrange(0, self.world.width)
        y = self.random.randrange(0, self.world.height)
        return x, y

    def create_initial_organism(
        self,
        energy: float,
        minimum_weight: float = -1.0,
        maximum_weight: float = 1.0,
    ) -> Organism:
        x, y = self.random_position()
        direction = self.random.choice(list(Direction))

        genome = Genome.random_genome(
            random_generator=self.random,
            reproduction_threshold=(
                self.config.initial_reproduction_threshold
            ),
            minimum_weight=minimum_weight,
            maximum_weight=maximum_weight,
        )

        organism = self._build_organism(
            genome=genome,
            energy=energy,
            x=x,
            y=y,
            direction=direction,
            parent_id=None,
            birth_tick=0,
            mutated_weight_count=None,
        )

        self.organisms.append(organism)

        return organism

    def _build_organism(
        self,
        genome: Genome,
        energy: float,
        x: int,
        y: int,
        direction: Direction,
        parent_id: int | None,
        birth_tick: int,
        mutated_weight_count: int | None,
    ) -> Organism:
        organism_id = self.next_organism_id
        self.next_organism_id += 1

        brain = NeuralNetwork(genome)
        organism = Organism(
            organism_id=organism_id,
            genome=genome,
            brain=brain,
            energy=energy,
            x=x,
            y=y,
            direction=direction,
            parent_id=parent_id,
            birth_tick=birth_tick,
        )

        self.metrics.organism_metrics[organism_id] = OrganismMetrics(
            organism_id=organism_id,
            genome=genome,
            action_counts=new_action_counts(),
            parent_id=parent_id,
            birth_tick=birth_tick,
            mutated_weight_count=mutated_weight_count,
            initial_energy=energy,
            final_energy=energy,
            peak_energy=energy,
        )

        return organism
    
    def step(self) -> TickMetrics:
        self.tick += 1

        tick_metrics = TickMetrics(
            tick=self.tick,
            starting_population=len(self.organisms),
            action_counts=new_action_counts(),
        )

        surviving_organisms: list[Organism] = []

        for organism in self.organisms:
            organism_metrics = self.metrics.organism_metrics[
                organism.organism_id
            ]

            cell = self.world.get_cell(organism.x, organism.y)
            sensed_energy = cell.energy

            normalized_cell_energy = (
                sensed_energy
                / self.config.maximum_cell_energy
            )

            normalized_stored_energy = (
                organism.energy
                / self.config.initial_organism_energy
            )

            sensor_values = {
                Sensor.CELL_ENERGY: normalized_cell_energy,
                Sensor.STORED_ENERGY: normalized_stored_energy,
                Sensor.BIAS: 1.0,
            }


            action, activations = organism.brain.choose_action(
                sensor_values=sensor_values,
                random_generator=self.random,
            )
            _ = activations

            tick_metrics.action_counts[action] += 1
            self.metrics.action_counts[action] += 1
            organism_metrics.action_counts[action] += 1
            organism_metrics.final_action = action

            energy_eaten = self.execute_action(
                organism=organism,
                action=action,
            )

            if action == Action.EAT:
                if energy_eaten > 0.0:
                    tick_metrics.successful_eats += 1
                    self.metrics.successful_eats += 1
                    organism_metrics.successful_eats += 1

                    tick_metrics.energy_eaten += energy_eaten
                    self.metrics.total_energy_eaten += energy_eaten
                    organism_metrics.energy_eaten += energy_eaten

                    if (
                        organism_metrics.first_successful_eat_tick
                        is None
                    ):
                        organism_metrics.first_successful_eat_tick = (
                            self.tick
                        )
                    organism_metrics.last_successful_eat_tick = (
                        self.tick
                    )

                    if self.metrics.first_successful_eat_tick is None:
                        self.metrics.first_successful_eat_tick = (
                            self.tick
                        )
                    self.metrics.last_successful_eat_tick = self.tick

                    if self.tick == 1:
                        self.metrics.tick_one_energy_eaten += (
                            energy_eaten
                        )
                    else:
                        self.metrics.after_tick_one_energy_eaten += (
                            energy_eaten
                        )
                else:
                    tick_metrics.unsuccessful_eats += 1
                    self.metrics.unsuccessful_eats += 1
                    organism_metrics.unsuccessful_eats += 1

            organism_metrics.peak_energy = max(
                organism_metrics.peak_energy,
                organism.energy,
            )

            self.burn_energy(organism, action)

            died_this_tick = organism.energy <= 0.0

            if died_this_tick:
                organism.energy = 0.0
                organism_metrics.death_tick = self.tick
            else:
                surviving_organisms.append(organism)

            organism_metrics.final_energy = organism.energy

        tick_metrics.deaths = (
            tick_metrics.starting_population
            - len(surviving_organisms)
        )

        newborns = self._reproduce(surviving_organisms)
        tick_metrics.births = len(newborns)

        self.organisms = surviving_organisms + newborns
        tick_metrics.ending_population = len(self.organisms)
        self.metrics.peak_population = max(
            self.metrics.peak_population,
            tick_metrics.ending_population,
        )

        regeneration = self.regenerate_environmental_energy()
        tick_metrics.regeneration_cells_selected = len(
            regeneration.selected_cell_indices
        )
        tick_metrics.regeneration_energy_attempted = (
            regeneration.attempted_energy
        )
        tick_metrics.regeneration_energy_added = (
            regeneration.actual_energy_added
        )
        tick_metrics.regeneration_energy_wasted = (
            regeneration.wasted_energy
        )
        self.metrics.regeneration_energy_attempted += (
            regeneration.attempted_energy
        )
        self.metrics.regeneration_energy_added += (
            regeneration.actual_energy_added
        )
        self.metrics.regeneration_energy_wasted += (
            regeneration.wasted_energy
        )

        self.metrics.tick_history.append(tick_metrics)
        return tick_metrics

    def _reproduce(
        self,
        surviving_organisms: list[Organism],
    ) -> list[Organism]:
        occupied_positions = {
            (organism.x, organism.y)
            for organism in surviving_organisms
        }

        eligible_parents = [
            organism
            for organism in surviving_organisms
            if self._can_reproduce(organism)
        ]
        if not eligible_parents:
            return []

        reproduction_order = eligible_parents.copy()
        self.random.shuffle(reproduction_order)

        newborns: list[Organism] = []
        for parent in reproduction_order:
            child = self._try_reproduce(
                parent=parent,
                occupied_positions=occupied_positions,
            )
            if child is not None:
                newborns.append(child)

        return newborns

    def _can_reproduce(self, parent: Organism) -> bool:
        return (
            parent.energy >= parent.genome.reproduction_threshold
            and (
                parent.energy
                - self.config.reproduction_energy_cost
            ) > 0.0
        )

    def _try_reproduce(
        self,
        parent: Organism,
        occupied_positions: set[tuple[int, int]],
    ) -> Organism | None:
        if not self._can_reproduce(parent):
            return None

        available_positions = [
            position
            for position in self.world.neighboring_positions(
                parent.x,
                parent.y,
            )
            if position not in occupied_positions
        ]
        if not available_positions:
            return None

        child_x, child_y = self.random.choice(
            available_positions
        )
        parent_energy_before = parent.energy
        shared_energy = (
            parent_energy_before
            - self.config.reproduction_energy_cost
        ) / 2.0
        parent.energy = shared_energy

        child_genome = parent.genome.mutated_copy(
            random_generator=self.random,
            mutation_rate=self.config.mutation_rate,
            mutation_amount=self.config.mutation_amount,
        )
        mutated_weight_count = (
            child_genome.neural_weight_difference_count(parent.genome)
        )

        child = self._build_organism(
            genome=child_genome,
            energy=shared_energy,
            x=child_x,
            y=child_y,
            direction=parent.direction,
            parent_id=parent.organism_id,
            birth_tick=self.tick,
            mutated_weight_count=mutated_weight_count,
        )
        occupied_positions.add((child_x, child_y))

        parent_metrics = self.metrics.organism_metrics[
            parent.organism_id
        ]
        parent_metrics.final_energy = parent.energy
        parent_metrics.offspring_count += 1

        self.metrics.total_births += 1
        if self.metrics.first_birth_tick is None:
            self.metrics.first_birth_tick = self.tick
        self.metrics.last_birth_tick = self.tick

        self._assert_close(
            parent.energy + child.energy,
            parent_energy_before
            - self.config.reproduction_energy_cost,
            "reproduction energy conservation",
        )

        return child

    def regenerate_environmental_energy(
        self,
    ) -> EnvironmentalRegenerationResult:
        cell_count = self.config.regeneration_cell_count
        amount = self.config.regeneration_amount

        if cell_count == 0 or amount == 0.0:
            return EnvironmentalRegenerationResult(
                selected_cell_indices=(),
                attempted_energy=0.0,
                actual_energy_added=0.0,
                wasted_energy=0.0,
            )

        selected_cell_indices = tuple(
            self.random.sample(
                range(len(self.world.cells)),
                k=cell_count,
            )
        )
        attempted_energy = cell_count * amount
        actual_energy_added = 0.0

        for cell_index in selected_cell_indices:
            cell = self.world.cells[cell_index]
            energy_before = cell.energy
            cell.energy = min(
                self.config.maximum_cell_energy,
                energy_before + amount,
            )
            actual_energy_added += cell.energy - energy_before

        wasted_energy = attempted_energy - actual_energy_added
        return EnvironmentalRegenerationResult(
            selected_cell_indices=selected_cell_indices,
            attempted_energy=attempted_energy,
            actual_energy_added=actual_energy_added,
            wasted_energy=wasted_energy,
        )

    def execute_action(
        self,
        organism: Organism,
        action: Action,
    ) -> float:
        if action == Action.WAIT:
            return 0.0
        if action == Action.MOVE_FORWARD:
            next_x, next_y = self.world.move_forward_position(
                x=organism.x,
                y=organism.y,
                direction=organism.direction,
            )
            organism.x = next_x
            organism.y = next_y
            return 0.0
        elif action == Action.TURN_LEFT:
            organism.turn_left()
            return 0.0
        elif action == Action.TURN_RIGHT:
            organism.turn_right()
            return 0.0
        elif action == Action.EAT:
            cell = self.world.get_cell(organism.x, organism.y)
            return organism.eat(cell)

        raise ValueError(f"Unsupported action: {action}")

    def action_energy_cost(self, action: Action) -> float:
        if action == Action.WAIT:
            return self.config.wait_energy_cost
        if action == Action.EAT:
            return self.config.eat_energy_cost
        if action == Action.TURN_LEFT:
            return self.config.turn_left_energy_cost
        if action == Action.TURN_RIGHT:
            return self.config.turn_right_energy_cost
        if action == Action.MOVE_FORWARD:
            return self.config.move_forward_energy_cost

        raise ValueError(f"Unsupported action for energy cost: {action}")

    def burn_energy(self, organism: Organism, action: Action) -> None:
        action_cost = self.action_energy_cost(action)
        total_energy_cost = self.config.base_energy_cost_per_tick + action_cost
        organism.energy -= total_energy_cost

    def print_experiment_report(self) -> None:
        from experiments.report import (
            build_experiment_report,
            format_experiment_report,
        )

        print(format_experiment_report(build_experiment_report(self)))

    def _longevity(self, metrics: OrganismMetrics) -> int:
        end_tick = self.tick if metrics.death_tick is None else metrics.death_tick
        return end_tick - metrics.birth_tick

    def _representative_from_metrics(
        self,
        candidates: list[OrganismMetrics],
    ) -> OrganismMetrics | None:
        if not candidates:
            return None
        return max(
            candidates,
            key=lambda metrics: (
                self._longevity(metrics),
                metrics.energy_eaten,
                metrics.action_counts[Action.MOVE_FORWARD],
                -metrics.organism_id,
            ),
        )

    def _assert_close(
        self,
        left: float,
        right: float,
        label: str,
    ) -> None:
        if abs(left - right) > 1e-9:
            raise AssertionError(
                f"Consistency check failed for {label}: "
                f"{left} != {right}"
            )

    def _run_consistency_checks(self) -> None:
        total_eat_actions = self.metrics.action_counts[Action.EAT]
        assert (
            self.metrics.successful_eats
            + self.metrics.unsuccessful_eats
            == total_eat_actions
        ), "successful_eats + unsuccessful_eats must equal total EAT actions"

        self._assert_close(
            self.metrics.tick_one_energy_eaten
            + self.metrics.after_tick_one_energy_eaten,
            self.metrics.total_energy_eaten,
            "tick_one_energy_eaten + after_tick_one_energy_eaten",
        )

        remaining_world_energy = self.total_world_energy()
        expected_energy_eaten = (
            self.initial_world_energy
            + self.metrics.regeneration_energy_added
            - remaining_world_energy
        )

        self._assert_close(
            self.metrics.total_energy_eaten,
            expected_energy_eaten,
            "total_energy_eaten == initial world energy plus regenerated "
            "energy minus remaining world energy",
        )

        self._assert_close(
            self.metrics.regeneration_energy_attempted,
            self.metrics.regeneration_energy_added
            + self.metrics.regeneration_energy_wasted,
            "attempted regeneration == added regeneration + wasted regeneration",
        )

        self._assert_close(
            sum(
                tick.regeneration_energy_attempted
                for tick in self.metrics.tick_history
            ),
            self.metrics.regeneration_energy_attempted,
            "per-tick attempted regeneration",
        )
        self._assert_close(
            sum(
                tick.regeneration_energy_added
                for tick in self.metrics.tick_history
            ),
            self.metrics.regeneration_energy_added,
            "per-tick added regeneration",
        )
        self._assert_close(
            sum(
                tick.regeneration_energy_wasted
                for tick in self.metrics.tick_history
            ),
            self.metrics.regeneration_energy_wasted,
            "per-tick wasted regeneration",
        )

        total_organism_turns = sum(
            tick_metrics.starting_population
            for tick_metrics in self.metrics.tick_history
        )
        assert (
            sum(self.metrics.action_counts.values())
            == total_organism_turns
        ), "sum(action_counts) must equal total organism turns"

        per_organism_action_counts = new_action_counts()
        for organism_metrics in self.metrics.organism_metrics.values():
            for action, count in organism_metrics.action_counts.items():
                per_organism_action_counts[action] += count

        assert (
            per_organism_action_counts
            == self.metrics.action_counts
        ), "per-organism action counts must equal experiment action counts"

        for tick_metrics in self.metrics.tick_history:
            assert (
                tick_metrics.ending_population
                == tick_metrics.starting_population
                - tick_metrics.deaths
                + tick_metrics.births
            ), (
                "ending population must equal starting population "
                "minus deaths plus births"
            )

        assert (
            sum(
                tick_metrics.births
                for tick_metrics in self.metrics.tick_history
            )
            == self.metrics.total_births
        ), "per-tick births must equal total births"

        assert (
            self.metrics.total_births
            == self.next_organism_id
            - self.config.initial_organisms
        ), "total births must equal organisms created after the Big Bang"

        assert (
            sum(
                metrics.offspring_count
                for metrics in self.metrics.organism_metrics.values()
            )
            == self.metrics.total_births
        ), "per-organism offspring counts must equal total births"

        for organism_id, metrics in (
            self.metrics.organism_metrics.items()
        ):
            assert all(
                count >= 0 for count in metrics.action_counts.values()
            ), "per-organism action counts must be nonnegative"
            assert (
                metrics.successful_eats + metrics.unsuccessful_eats
                == metrics.action_counts[Action.EAT]
            ), "per-organism EAT outcomes must equal EAT actions"
            organism_action_total = sum(metrics.action_counts.values())
            assert (metrics.final_action is None) == (organism_action_total == 0), (
                "final action must exist exactly when an organism has acted"
            )
            if organism_id < self.config.initial_organisms:
                assert metrics.parent_id is None, (
                    "initial organisms must not have a parent"
                )
                assert metrics.birth_tick == 0, (
                    "initial organisms must have birth_tick 0"
                )
                assert metrics.mutated_weight_count is None, (
                    "initial organisms must not have mutation metadata"
                )
            else:
                assert metrics.parent_id is not None, (
                    "offspring must have a parent"
                )
                assert (
                    metrics.parent_id
                    in self.metrics.organism_metrics
                ), "offspring parent must reference a known organism"
                assert metrics.birth_tick >= 1, (
                    "offspring birth_tick must be at least 1"
                )
                assert metrics.mutated_weight_count is not None, (
                    "offspring must have mutation metadata"
                )
                assert 0 <= metrics.mutated_weight_count <= (
                    len(Action) * len(Sensor)
                ), "offspring mutation count must fit neural topology"

                parent_metrics = self.metrics.organism_metrics[
                    metrics.parent_id
                ]
                assert metrics.mutated_weight_count == (
                    metrics.genome.neural_weight_difference_count(
                        parent_metrics.genome
                    )
                ), "offspring mutation count must match its parent genome"

        if self.metrics.total_births == 0:
            assert self.metrics.first_birth_tick is None
            assert self.metrics.last_birth_tick is None
        else:
            assert self.metrics.first_birth_tick is not None
            assert self.metrics.last_birth_tick is not None
            assert (
                self.metrics.first_birth_tick
                <= self.metrics.last_birth_tick
            )

        observed_populations = [
            self.config.initial_organisms,
            *(
                tick_metrics.ending_population
                for tick_metrics in self.metrics.tick_history
            ),
        ]
        assert self.metrics.peak_population == max(
            observed_populations
        ), "peak population must match observed populations"

        if not self.organisms:
            assert all(
                metrics.death_tick is not None
                for metrics in self.metrics.organism_metrics.values()
            ), "at extinction, every organism must have a death_tick"

            latest_death_tick = max(
                (
                    metrics.death_tick
                    for metrics in self.metrics.organism_metrics.values()
                    if metrics.death_tick is not None
                ),
                default=0,
            )

            assert (
                self.tick == latest_death_tick
            ), "at extinction, final tick must equal latest death tick"
    
