from domain.simulation import Simulation
from domain.simulation_config import SimulationConfig


def main() -> None:
    config = SimulationConfig(
        seed=4,
        world_width=20,
        world_height=20,
        initial_organisms=2,
        initial_organism_energy=100.0,
        minimum_cell_energy=0,
        maximum_cell_energy=10,
        minimum_initial_weight=-1.0,
        maximum_initial_weight=1.0,
        base_energy_cost_per_tick=1.0,
        wait_energy_cost=0.00,
        eat_energy_cost=0.25,
        turn_left_energy_cost=0.50,
        turn_right_energy_cost=0.50,
        move_forward_energy_cost=1.00,
    )

    simulation = Simulation.big_bang(config)

    # simulation.print_initial_state()

    for _ in range(9):
        simulation.step()


if __name__ == "__main__":
    main()