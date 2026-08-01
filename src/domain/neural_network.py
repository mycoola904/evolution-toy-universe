class NeuralNetwork:
    def __init__(self, genome):
        self.genome = genome

    def evaluate(self, inputs: list[float]) -> list[float]:
        activations = []

        for weight in self.genome.weights:
            activation = inputs[0] * weight
            activations.append(activation)
            
        return activations
        