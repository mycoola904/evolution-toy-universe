import pytest

from domain.cell import Cell
from domain.world import World


def make_world(width: int, height: int) -> World:
    return World(
        width=width,
        height=height,
        cells=[Cell() for _ in range(width * height)],
    )


@pytest.mark.parametrize(
    ("width", "height", "position", "expected"),
    [
        (
            5,
            5,
            (0, 0),
            [(0, 4), (1, 0), (0, 1), (4, 0)],
        ),
        (1, 1, (0, 0), [(0, 0)]),
        (1, 2, (0, 0), [(0, 1), (0, 0)]),
        (2, 1, (0, 0), [(0, 0), (1, 0)]),
        (2, 2, (0, 0), [(0, 1), (1, 0)]),
    ],
)
def test_neighboring_positions_are_wrapped_unique_and_stable(
    width,
    height,
    position,
    expected,
):
    world = make_world(width, height)

    assert world.neighboring_positions(*position) == expected

