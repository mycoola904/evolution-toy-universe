import random

from domain.world import World
from domain.simulation_config import SimulationConfig
from domain.cell import Cell
from domain.organism import Organism
from domain.genome import Genome
from domain.neural_network import NeuralNetwork
from domain.direction import Direction
from domain.action import Action

class Simulation:
    def __init__(self, world: World, seed: int):
        self.random = random.Random(seed)   
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
            seed=config.seed,
        )

        simulation.initialize_cell_energy(
            minimum_energy=config.minimum_cell_energy,
            maximum_energy=config.maximum_cell_energy,
        )

        for _ in range(config.initial_organisms):
            simulation.create_initial_organism(
                energy=config.initial_organism_energy,
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

    def create_initial_organism(self, energy: float) -> Organism:
        x, y = self.random_position()
        direction = self.random.choice(list(Direction))

        genome = Genome()
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
            action = self.choose_action(organism)
            self.execute_action(organism, action)
            final_location = (organism.x, organism.y)

            self._print_organism_step(
                index=index,
                organism=organism,
                action=action,
                previous_location=previous_location,
                final_location=final_location,
            )

    def choose_action(self, organism: Organism) -> Action:
        _ = organism
        return self.random.choice(list(Action))

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
            

    def _print_organism_step(
    self,
    index: int,
    organism: Organism,
    action: Action,
    previous_location: tuple[int, int],
    final_location: tuple[int, int],
    ) -> None:
        print(f"Organism {index}:")
        print(f"  Direction: {organism.direction.name}")
        print(f"  Action: {action.name}")
        print(f"  Previous location: {previous_location}")
        print(f"  Final location: {final_location}")
        print(f"  Energy: {organism.energy}")

    
