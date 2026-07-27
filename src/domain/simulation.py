class Simulation:
    def __init__(self, world):
        self.world = world
        self.tick = 0
        self.organisms = []

    def step(self):
        self.tick += 1

        print(f"Tick: {self.tick}")
               
