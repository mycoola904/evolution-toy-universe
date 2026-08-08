from domain.simulation import Simulation
from domain.simulation_config import SimulationConfig
from domain.action import Action


def main() -> None:
    config = SimulationConfig(
        seed=3,
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

    maximum_ticks = 10_000
    progress_interval = 10

    while (
        simulation.organisms
        and simulation.tick < maximum_ticks
    ):
        tick_metrics = simulation.step()

        should_print_progress = (
            tick_metrics.tick == 1
            or tick_metrics.tick % progress_interval == 0
            or tick_metrics.ending_population == 0
        )

        if should_print_progress:
            print(
                f"Tick {tick_metrics.tick:<5}"
                f"| Population {tick_metrics.ending_population:<4} "
                f"| Deaths {tick_metrics.deaths:<3} "
                f"| Ate {tick_metrics.energy_eaten:8.2f} "
                f"| Moves {tick_metrics.action_counts[Action.MOVE_FORWARD]}"
            )

    simulation.print_experiment_report()


if __name__ == "__main__":
    main()