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
        self.organisms = []
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
            maximum_weight: float = 1.0
        ) -> Organism:
        organism_id = self.next_organism_id
        self.next_organism_id += 1

        x, y = self.random_position()
        direction = self.random.choice(list(Direction))

        genome = Genome.random_genome(
            random_generator=self.random,
            minimum_weight=minimum_weight,
            maximum_weight=maximum_weight,
        )

        brain = NeuralNetwork(genome)

        organism = Organism(
            organism_id=organism_id,
            genome=genome,
            brain=brain,
            energy=energy,
            x=x,
            y=y,
            direction=direction,
        )

        self.organisms.append(organism)

        self.metrics.organism_metrics[organism_id] = OrganismMetrics(
            organism_id=organism_id,
            genome=genome,
            action_counts=new_action_counts(),
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

        self.organisms = surviving_organisms

        tick_metrics.ending_population = len(
            surviving_organisms
        )
        tick_metrics.deaths = (
            tick_metrics.starting_population
            - tick_metrics.ending_population
        )

        self.metrics.tick_history.append(tick_metrics)
        return tick_metrics

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
        self._run_consistency_checks()

        remaining_world_energy = self.total_world_energy()

        consumed_world_energy = (
            self.initial_world_energy
            - remaining_world_energy
        )

        if self.initial_world_energy > 0:
            percent_consumed = (
                consumed_world_energy
                / self.initial_world_energy
                * 100.0
            )

            percent_remaining = (
                remaining_world_energy
                / self.initial_world_energy
                * 100.0
            )
        else:
            percent_consumed = 0.0
            percent_remaining = 0.0

        if self.organisms:
            status = "TICK LIMIT REACHED"
        else:
            status = "POPULATION EXTINCT"

        organism_metrics = list(
            self.metrics.organism_metrics.values()
        )

        total_action_count = sum(
            self.metrics.action_counts.values()
        )
        total_eat_attempts = self.metrics.action_counts[
            Action.EAT
        ]
        total_move_actions = self.metrics.action_counts[
            Action.MOVE_FORWARD
        ]

        organisms_that_ate = sum(
            1
            for metrics in organism_metrics
            if metrics.successful_eats > 0
        )
        organisms_that_moved = [
            metrics
            for metrics in organism_metrics
            if metrics.action_counts[Action.MOVE_FORWARD] > 0
        ]

        most_moves = max(
            (
                metrics.action_counts[Action.MOVE_FORWARD]
                for metrics in organism_metrics
            ),
            default=0,
        )

        most_move_ids = sorted(
            metrics.organism_id
            for metrics in organism_metrics
            if metrics.action_counts[Action.MOVE_FORWARD] == most_moves
            and most_moves > 0
        )

        longest_survival_tick = max(
            (
                self._survival_tick(metrics)
                for metrics in organism_metrics
            ),
            default=0,
        )

        longest_surviving_metrics = [
            metrics
            for metrics in organism_metrics
            if self._survival_tick(metrics)
            == longest_survival_tick
        ]
        longest_surviving_ids = sorted(
            metrics.organism_id
            for metrics in longest_surviving_metrics
        )

        latest_death_tick = max(
            (
                metrics.death_tick
                for metrics in organism_metrics
                if metrics.death_tick is not None
            ),
            default=None,
        )

        representative_last_survivor = (
            self._representative_last_survivor()
        )

        longest_lived = self._representative_from_metrics(
            longest_surviving_metrics
        )
        largest_energy_consumer = self._best_by_value(
            organism_metrics,
            lambda metrics: metrics.energy_eaten,
        )
        most_mobile = self._best_by_value(
            organism_metrics,
            lambda metrics: metrics.action_counts[
                Action.MOVE_FORWARD
            ],
        )
        highest_peak = self._best_by_value(
            organism_metrics,
            lambda metrics: metrics.peak_energy,
        )

        print()
        self._print_report_banner("EXPERIMENT REPORT")
        self._print_report_section("EXPERIMENT SUMMARY")
        self._print_report_kv("Status", status)
        self._print_report_kv("Seed", str(self.config.seed))
        self._print_report_kv(
            "World dimensions",
            f"{self.config.world_width}x{self.config.world_height}",
        )
        self._print_report_kv("Final tick", self._format_count(self.tick))
        self._print_report_kv(
            "Initial population",
            self._format_count(self.config.initial_organisms),
        )
        self._print_report_kv(
            "Remaining population",
            self._format_count(len(self.organisms)),
        )

        self._print_report_section("ENVIRONMENTAL ENERGY")
        self._print_report_kv(
            "Initial world energy",
            f"{self.initial_world_energy:.2f}",
        )
        self._print_report_kv(
            "Remaining world energy",
            f"{remaining_world_energy:.2f}",
        )
        self._print_report_kv(
            "World energy consumed",
            f"{consumed_world_energy:.2f}",
        )
        self._print_report_kv(
            "Percent consumed",
            f"{percent_consumed:.2f}%",
        )
        self._print_report_kv(
            "Percent left stranded",
            f"{percent_remaining:.2f}%",
        )
        self._print_report_kv(
            "Energy eaten on tick 1",
            f"{self.metrics.tick_one_energy_eaten:.2f}",
        )
        self._print_report_kv(
            "Energy eaten after tick 1",
            f"{self.metrics.after_tick_one_energy_eaten:.2f}",
        )
        if consumed_world_energy > 0.0:
            percent_after_tick_one = (
                self.metrics.after_tick_one_energy_eaten
                / consumed_world_energy
                * 100.0
            )
        else:
            percent_after_tick_one = 0.0
        self._print_report_kv(
            "Percent of consumed energy eaten after tick 1",
            f"{percent_after_tick_one:.2f}%",
        )
        self._print_report_kv(
            "First successful EAT tick",
            self._format_tick(self.metrics.first_successful_eat_tick),
        )
        self._print_report_kv(
            "Last successful EAT tick",
            self._format_tick(self.metrics.last_successful_eat_tick),
        )

        self._print_report_section("ACTION TOTALS")
        print(f"{'Action':<13} {'Count':>10} {'Percent':>10}")
        for action in Action:
            count = self.metrics.action_counts[action]
            if total_action_count > 0:
                percentage = count / total_action_count * 100.0
            else:
                percentage = 0.0
            print(
                f"{action.name:<13} "
                f"{count:>10,} "
                f"{percentage:>9.2f}%"
            )

        self._print_report_section("EATING RESULTS")
        self._print_report_kv(
            "Total EAT attempts",
            self._format_count(total_eat_attempts),
        )
        self._print_report_kv(
            "Successful EAT actions",
            self._format_count(self.metrics.successful_eats),
        )
        self._print_report_kv(
            "Unsuccessful EAT actions",
            self._format_count(self.metrics.unsuccessful_eats),
        )
        if total_eat_attempts > 0:
            eat_success_rate = (
                self.metrics.successful_eats
                / total_eat_attempts
                * 100.0
            )
        else:
            eat_success_rate = 0.0
        self._print_report_kv("EAT success rate", f"{eat_success_rate:.2f}%")
        self._print_report_kv(
            "Organisms that successfully ate",
            self._format_count(organisms_that_ate),
        )
        self._print_report_kv(
            "Total energy eaten",
            f"{self.metrics.total_energy_eaten:.2f}",
        )

        self._print_report_section("MOVEMENT RESULTS")
        self._print_report_kv(
            "Total MOVE_FORWARD actions",
            self._format_count(total_move_actions),
        )
        self._print_report_kv(
            "Organisms that moved at least once",
            self._format_count(len(organisms_that_moved)),
        )
        self._print_report_kv(
            "Most moves by one organism",
            self._format_count(most_moves),
        )
        if most_move_ids:
            self._print_report_kv(
                "Organism ID with the most moves",
                str(most_move_ids[0]),
            )
            self._print_report_kv(
                "Organism IDs tied for most moves",
                self._format_id_list(most_move_ids),
            )
        else:
            self._print_report_kv(
                "Organism ID with the most moves",
                "NONE",
            )

        self._print_report_section("SURVIVAL RESULTS")
        self._print_report_kv(
            "Last death tick",
            self._format_tick(latest_death_tick),
        )
        self._print_report_kv(
            "Longest-surviving organism IDs",
            self._format_id_list(longest_surviving_ids),
        )
        self._print_report_kv(
            "Number tied for longest survival",
            self._format_count(len(longest_surviving_ids)),
        )

        self._print_report_section("NOTABLE ORGANISMS")
        self._print_notable_organism(
            label="Longest-lived organism",
            metrics=longest_lived,
        )
        self._print_notable_organism(
            label="Largest energy consumer",
            metrics=largest_energy_consumer,
        )
        self._print_notable_organism(
            label="Most mobile organism",
            metrics=most_mobile,
        )
        self._print_notable_organism(
            label="Highest peak-energy organism",
            metrics=highest_peak,
        )

        self._print_report_section("REPRESENTATIVE LAST-SURVIVOR GENOME")
        if representative_last_survivor is None:
            print("No organism metrics recorded.")
        else:
            self._print_report_kv(
                "Representative organism ID",
                str(representative_last_survivor.organism_id),
            )
            self._print_report_kv(
                "Longest-surviving IDs",
                self._format_id_list(longest_surviving_ids),
            )
            self._print_genome(
                representative_last_survivor.genome
            )
        self._print_report_footer()

    def _survival_tick(
        self,
        metrics: OrganismMetrics,
    ) -> int:
        if metrics.death_tick is None:
            return self.tick
        return metrics.death_tick

    def _best_by_value(
        self,
        candidates: list[OrganismMetrics],
        value_fn,
    ) -> OrganismMetrics | None:
        if not candidates:
            return None

        best_value = max(value_fn(metrics) for metrics in candidates)
        best_candidates = [
            metrics
            for metrics in candidates
            if value_fn(metrics) == best_value
        ]
        return self._representative_from_metrics(best_candidates)

    def _representative_from_metrics(
        self,
        candidates: list[OrganismMetrics],
    ) -> OrganismMetrics | None:
        if not candidates:
            return None

        return max(
            candidates,
            key=lambda metrics: (
                self._survival_tick(metrics),
                metrics.energy_eaten,
                metrics.action_counts[Action.MOVE_FORWARD],
                -metrics.organism_id,
            ),
        )

    def _representative_last_survivor(
        self,
    ) -> OrganismMetrics | None:
        all_metrics = list(
            self.metrics.organism_metrics.values()
        )
        if not all_metrics:
            return None

        if self.organisms:
            surviving_ids = {
                organism.organism_id
                for organism in self.organisms
            }
            candidates = [
                metrics
                for metrics in all_metrics
                if metrics.organism_id in surviving_ids
            ]
        else:
            latest_death_tick = max(
                (
                    metrics.death_tick
                    for metrics in all_metrics
                    if metrics.death_tick is not None
                ),
                default=None,
            )

            candidates = [
                metrics
                for metrics in all_metrics
                if metrics.death_tick == latest_death_tick
            ]

        return self._representative_from_metrics(candidates)

    def _print_notable_organism(
        self,
        label: str,
        metrics: OrganismMetrics | None,
    ) -> None:
        print(label + ":")
        if metrics is None:
            print("  None")
            return

        if metrics.final_action is None:
            final_action = "NONE"
        else:
            final_action = metrics.final_action.name

        self._print_report_kv(
            "Organism ID",
            str(metrics.organism_id),
            indent=2,
        )
        self._print_report_kv(
            "Death tick",
            self._format_tick(metrics.death_tick),
            indent=2,
        )
        self._print_report_kv(
            "Successful eats",
            self._format_count(metrics.successful_eats),
            indent=2,
        )
        self._print_report_kv(
            "Energy eaten",
            f"{metrics.energy_eaten:.2f}",
            indent=2,
        )
        self._print_report_kv(
            "Moves",
            self._format_count(
                metrics.action_counts[Action.MOVE_FORWARD]
            ),
            indent=2,
        )
        self._print_report_kv(
            "Peak energy",
            f"{metrics.peak_energy:.2f}",
            indent=2,
        )
        self._print_report_kv(
            "Final action",
            final_action,
            indent=2,
        )

    def _print_genome(self, genome: Genome) -> None:
        for action in Action:
            print(f"{action.name}:")
            sensor_weights = genome.weights[action]

            for sensor in Sensor:
                weight = sensor_weights[sensor]
                print(
                    f"  {sensor.name:<15}: "
                    f"{weight:6.2f}"
                )

            print()

    def _print_report_banner(self, title: str) -> None:
        separator = "=" * 60
        print(separator)
        print(title)
        print(separator)

    def _print_report_section(self, title: str) -> None:
        separator = "-" * 60
        print(separator)
        print(title)

    def _print_report_footer(self) -> None:
        print("=" * 60)

    def _print_report_kv(
        self,
        label: str,
        value: str,
        indent: int = 0,
        label_width: int = 44,
    ) -> None:
        prefix = " " * indent
        print(
            f"{prefix}{label:<{label_width}} "
            f"{value}"
        )

    def _format_count(self, value: int) -> str:
        return f"{value:,}"

    def _format_tick(self, tick: int | None) -> str:
        if tick is None:
            return "NONE"
        return str(tick)

    def _format_id_list(self, ids: list[int]) -> str:
        if not ids:
            return "NONE"
        return ", ".join(str(identifier) for identifier in ids)

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
        consumed_world_energy = (
            self.initial_world_energy
            - remaining_world_energy
        )

        self._assert_close(
            self.metrics.total_energy_eaten,
            consumed_world_energy,
            "total_energy_eaten == initial_world_energy - remaining_world_energy",
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
    
