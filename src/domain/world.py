class World:
    def __init__(self, width, height, cells):
        self.width = width
        self.height = height
        self.cells = cells

    def get_cell(self, x: int, y: int):
        if 0 <= x < self.width and 0 <= y < self.height:
            index = y * self.width + x
            return self.cells[index]
        else:
            raise IndexError("Cell coordinates out of bounds")