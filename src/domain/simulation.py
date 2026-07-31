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
            simulation.create_initial_organism()

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

    def create_initial_organism(self) -> Organism:
        x, y = self.random_position()
        direction = self.random.choice(list(Direction))

        genome = Genome()
        brain = NeuralNetwork(genome)

        organism = Organism(
            genome=genome,
            brain=brain,
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
            direction_before = organism.direction
            action = self.choose_action(organism)
            self.execute_action(organism, action)
            direction_after = organism.direction

            self._print_organism_step(
                index=index,
                organism=organism,
                action=action,
                direction_before=direction_before,
                direction_after=direction_after,
            )

    def choose_action(self, organism: Organism) -> Action:
        _ = organism
        return self.random.choice([Action.TURN_LEFT, Action.TURN_RIGHT])

    def execute_action(self, organism: Organism, action: Action) -> None:
        if action == Action.TURN_LEFT:
            organism.turn_left()
        elif action == Action.TURN_RIGHT:
            organism.turn_right()
            

    def _print_organism_step(
    self,
    index: int,
    organism: Organism,
    action: Action,
    direction_before: Direction,
    direction_after: Direction,
    ) -> None:
        print(f"Organism {index}:")
        print(f"  Position: ({organism.x}, {organism.y})")
        print(f"  Action: {action.name}")
        print(f"  Direction before action: {direction_before.name}")
        print(f"  Direction after action: {direction_after.name}")

    
