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

        print(f"Tick: {self.tick}")

    
