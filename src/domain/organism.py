from domain.direction import Direction
from domain.cell import Cell
class Organism:
    def __init__(
        self,
        genome,
        brain,
        energy: float = 100.0,
        x: int = 0,
        y: int = 0,
        direction: Direction = Direction.NORTH,
    ):
        self.x = x
        self.y = y

        self.direction = direction

        self.energy = energy

        self.genome = genome
        self.brain = brain

    def turn_left(self) -> None:
        if self.direction == Direction.NORTH:
            self.direction = Direction.WEST
        elif self.direction == Direction.WEST:
            self.direction = Direction.SOUTH
        elif self.direction == Direction.SOUTH:
            self.direction = Direction.EAST
        elif self.direction == Direction.EAST:
            self.direction = Direction.NORTH

    def turn_right(self) -> None:
        if self.direction == Direction.NORTH:
            self.direction = Direction.EAST
        elif self.direction == Direction.EAST:
            self.direction = Direction.SOUTH
        elif self.direction == Direction.SOUTH:
            self.direction = Direction.WEST
        elif self.direction == Direction.WEST:
            self.direction = Direction.NORTH

    # The organism eats the energy from the cell it is currently on
    def eat(self, cell: Cell):
        energy_eaten = cell.energy
        self.energy += energy_eaten
        cell.energy -= energy_eaten