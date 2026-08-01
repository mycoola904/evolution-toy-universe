import random


from domain.action import Action

class NeuralNetwork:
    def __init__(self, genome):
        self.genome = genome

    def evaluate(self, input_value: float) -> list[float]:
        activations = []

        for weight in self.genome.weights:
            activations.append(input_value * weight)
            
        return activations

    def choose_action(
            self, 
            input_value: float,
            random_generator: random.Random,
    ) -> tuple[Action, list[float]]:
        activations = self.evaluate(input_value)
        highest_activation = max(activations)
        actions = list(Action)

        tied_actions = [
            action
            for action, activation in zip(actions, activations) 
            if activation == highest_activation
            ]

        chosen_action = random_generator.choice(tied_actions)
        
        return chosen_action, activations
        