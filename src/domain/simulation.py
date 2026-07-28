import random

from domain.world import World

class Simulation:
    def __init__(self, world: World, seed: int):
        if seed is not None:
            random.seed(seed)
        self.world = world
        self.tick = 0
        self.organisms = []

    def step(self):
        self.tick += 1

        print(f"Tick: {self.tick}")
               
