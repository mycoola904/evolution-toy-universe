from domain.simulation import Simulation
from domain.simulation_config import SimulationConfig


def main() -> None:
    config = SimulationConfig(
        seed=42,
        world_width=20,
        world_height=20,
        initial_organisms=2,
        minimum_cell_energy=0,
        maximum_cell_energy=10,
    )

    simulation = Simulation.big_bang(config)

    # simulation.print_initial_state()

    for _ in range(1):
        simulation.step()


if __name__ == "__main__":
    main()