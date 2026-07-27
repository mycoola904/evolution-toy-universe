from domain.genome import Genome
from domain.neural_network import NeuralNetwork
from domain.organism import Organism
from domain.simulation import Simulation
from domain.cell import Cell
from domain.world import World

def main():

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


    simulation = Simulation(world)
    simulation.organisms.append(organism)

    print(f"Tick: {simulation.tick}")
    print(f"World size: {simulation.world.width} x {simulation.world.height}")
    print(f"Cells: {len(simulation.world.cells)}")
    print(f"Organisms: {len(simulation.organisms)}")
    print(f"Organism genome: {simulation.organisms[0].genome}")
    print(f"Organism brain: {simulation.organisms[0].brain}")

    # Run the simulation for a few steps
    for _ in range(10):
        simulation.step()
    

if __name__ == "__main__":
    main()