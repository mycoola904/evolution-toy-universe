from domain.simulation import Simulation
from domain.simulation_config import SimulationConfig


def main() -> None:
    config = SimulationConfig(
        seed=4,
        world_width=40,
        world_height=40,
        initial_organisms=100,
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

    maximum_ticks = 10_000

    while (
        simulation.organisms
        and simulation.tick < maximum_ticks
    ):
        simulation.step(show_details=True)

    simulation.print_experiment_report()


if __name__ == "__main__":
    main()