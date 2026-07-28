from domain.direction import Direction
from domain.cell import Cell
class Organism:
    def __init__(self, genome, brain, x: int = 0, y: int = 0):
        self.x = x
        self.y = y

        self.direction = Direction.NORTH

        self.energy = 100.0

        self.genome = genome
        self.brain = brain

    # The organism eats the energy from the cell it is currently on
    def eat(self, cell: Cell):
        energy_eaten = cell.energy
        self.energy += energy_eaten
        cell.energy -= energy_eaten