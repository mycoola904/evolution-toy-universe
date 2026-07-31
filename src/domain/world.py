from domain.direction import Direction


class World:
    def __init__(self, width, height, cells):
        self.width = width
        self.height = height
        self.cells = cells

    def wrap_position(self, x: int, y: int) -> tuple[int, int]:
        return x % self.width, y % self.height

    def move_forward_position(
        self,
        x: int,
        y: int,
        direction: Direction,
    ) -> tuple[int, int]:
        dx, dy = direction.value
        return self.wrap_position(x + dx, y + dy)

    def get_cell(self, x: int, y: int):
        if 0 <= x < self.width and 0 <= y < self.height:
            index = y * self.width + x
            return self.cells[index]
        else:
            raise IndexError("Cell coordinates out of bounds")