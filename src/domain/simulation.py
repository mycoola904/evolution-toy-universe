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

class Simulation:
    def __init__(
        self,
        world: World,
        config: SimulationConfig,
    ):
        self.config = config
        self.random = random.Random(config.seed)
        self.world = world
        self.tick = 0
        self.organisms = []


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
        x, y = self.random_position()
        direction = self.random.choice(list(Direction))

        genome = Genome.random_genome(
            random_generator=self.random,
            minimum_weight=minimum_weight,
            maximum_weight=maximum_weight,
        )

        brain = NeuralNetwork(genome)

        organism = Organism(
            genome=genome,
            brain=brain,
            energy=energy,
            x=x,
            y=y,
            direction=direction,
        )

        self.organisms.append(organism)

        return organism
    
    def step(self) -> None:
        self.tick += 1

        print(f"Tick: {self.tick}")

        for index, organism in enumerate(self.organisms):
            previous_location = (organism.x, organism.y)

            cell = self.world.get_cell(organism.x, organism.y)
            sensed_energy = cell.energy

            normalized_cell_energy = sensed_energy / self.config.maximum_cell_energy

            normalized_stored_energy = organism.energy / self.config.initial_organism_energy

            sensor_values = {
                Sensor.CELL_ENERGY: normalized_cell_energy,
                Sensor.STORED_ENERGY: normalized_stored_energy,
                Sensor.BIAS: 1.0,
            }


            action, activations = organism.brain.choose_action(
                sensor_values=sensor_values,
                random_generator=self.random,
            )


            self.execute_action(organism, action)
            energy_cost = self.burn_energy(organism, action)

            final_location = (organism.x, organism.y)

            self._print_organism_step(
                index=index,
                organism=organism,
                action=action,
                previous_location=previous_location,
                final_location=final_location,
                sensed_energy=sensed_energy,
                activations=activations,
                normalized_cell_energy=normalized_cell_energy,
                energy_cost=energy_cost,
            )

    def execute_action(self, organism: Organism, action: Action) -> None:
        if action == Action.WAIT:
            return
        if action == Action.MOVE_FORWARD:
            next_x, next_y = self.world.move_forward_position(
                x=organism.x,
                y=organism.y,
                direction=organism.direction,
            )
            organism.x = next_x
            organism.y = next_y
        elif action == Action.TURN_LEFT:
            organism.turn_left()
        elif action == Action.TURN_RIGHT:
            organism.turn_right()
        elif action == Action.EAT:
            cell = self.world.get_cell(organism.x, organism.y)
            organism.eat(cell)

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

    def burn_energy(self, organism: Organism, action: Action) -> float:
        action_cost = self.action_energy_cost(action)
        total_energy_cost = self.config.base_energy_cost_per_tick + action_cost
        organism.energy -= total_energy_cost
        return total_energy_cost
            

    def _print_organism_step(
        self,
        index: int,
        organism: Organism,
        action: Action,
        previous_location: tuple[int, int],
        final_location: tuple[int, int],
        sensed_energy: float = 0.0,
        activations: dict[Action, float] | None = None,
        normalized_cell_energy: float = 0.0,
        energy_cost: float = 0.0,
        normalized_stored_energy: float = 0.0
    ) -> None:
        print(f"Organism {index}:")
        print(f"  Direction: {organism.direction.name}")
        print(f"  Action: {action.name}")
        print(f"  Previous location: {previous_location}")
        print(f"  Final location: {final_location}")
        print(f"  Energy cost: {energy_cost:.2f}")
        print(f"  Energy: {organism.energy}")
        print(f"  Organism sensed energy: {sensed_energy}")
        print(f"  Normalized sensed energy: {normalized_cell_energy:.2f}")
        print(f"  Normalized stored energy: {normalized_stored_energy:.2f}")
        print("  Organism genome weights:")

        for action, sensor_weights in organism.genome.weights.items():
            print(f"    {action.name}:")

            for sensor, weight in sensor_weights.items():
                print(f"      {sensor.name:<15}: {weight:6.2f}")

        if activations is not None:
            print("  Organism activations:")

            for action, activation in activations.items():
                print(f"    {action.name:<15}: {activation:6.2f}")                

    
