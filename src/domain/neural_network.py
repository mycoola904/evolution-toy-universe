class NeuralNetwork:
    def __init__(self, genome):
        self.genome = genome

    def evaluate(self, input_value: float) -> list[float]:
        activations = []

        for weight in self.genome.weights:
            activations.append(input_value * weight)
            
        return activations
        