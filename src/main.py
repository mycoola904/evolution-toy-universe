from domain.genome import Genome
from domain.neural_network import NeuralNetwork
from domain.organism import Organism
from domain.simulation import Simulation
from domain.cell import Cell
from domain.world import World

def main():
    seed = 42  # Set a seed for reproducibility

    width = 20
    height = 20
    
    cells = [
        Cell() for _ in range(width * height)
    ]

    world = World(width, height, cells)

    genome = Genome()
    brain = NeuralNetwork(genome)

    organism = Organism(
        genome,
        brain
        )


    simulation = Simulation(world, seed)

    simulation.initialize_cell_energy(
        minimum_energy=0,
        maximum_energy=10
    )

    simulation.organisms.append(organism)

    # print(f"Tick: {simulation.tick}")
    # print(f"World size: {simulation.world.width} x {simulation.world.height}")
    # print(f"Cells: {len(simulation.world.cells)}")
    # print(f"Organisms: {len(simulation.organisms)}")
    # print(f"Organism genome: {simulation.organisms[0].genome}")
    # print(f"Organism brain: {simulation.organisms[0].brain}")

    total_energy = sum(cell.energy for cell in world.cells)

    energized_cells = sum(
        1
        for cell in world.cells
        if cell.energy > 0
    )

    first_ten_energy_values = [
        cell.energy
        for cell in world.cells[:10]
    ]


    print("=== Big Bang ===")
    print(f"Seed: {seed}")
    print(f"World size: {world.width} x {world.height}")
    print(f"Cells: {len(world.cells)}")
    print(f"Organisms: {len(simulation.organisms)}")
    print(f"Energized cells: {energized_cells}")
    print(f"Total environmental energy: {total_energy}")
    print(f"First 10 cell energies: {first_ten_energy_values}")


    current_cell = world.get_cell(
        organism.x,
        organism.y,
        )

    print(f"Organism initial position: ({organism.x}, {organism.y})")
    print(f"Organism initial energy: {current_cell.energy}")

    # Run the simulation for a few steps
    for _ in range(2):
        simulation.step()


if __name__ == "__main__":
    main()