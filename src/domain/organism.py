from domain.direction import Direction

class Organism:
    def __init__(self, genome, brain):
        self.x = 0
        self.y = 0

        self.direction = Direction.NORTH

        self.energy = 100.0

        self.genome = genome
        self.brain = brain