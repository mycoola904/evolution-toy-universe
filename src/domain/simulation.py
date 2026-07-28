import random

from domain.world import World

class Simulation:
    def __init__(self, world: World, seed: int):
        if seed is not None:
            random.seed(seed)
        self.random = random.Random(seed)   
        self.world = world
        self.tick = 0
        self.organisms = []

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
                           

    def step(self):
        self.tick += 1

        organism = self.organisms[0]
        cell = self.world.get_cell(organism.x, organism.y)


        print(f"Tick: {self.tick}")
        print(f"Cell energy before eating: {cell.energy}")
        print(f"Organism energy before eating: {organism.energy}")

        energy_before = organism.energy + cell.energy

        energy_eaten = cell.energy
        organism.energy += energy_eaten
        cell.energy -= energy_eaten

        energy_after = organism.energy + cell.energy
        print(f"Energy before eating: {energy_before}")
        print(f"Energy after eating: {energy_after}")
        print(f"Cell energy after eating: {cell.energy}")
        print(f"Organism energy after eating: {organism.energy}")

    
