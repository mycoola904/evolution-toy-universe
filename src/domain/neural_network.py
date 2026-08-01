import random


from domain.action import Action

class NeuralNetwork:
    def __init__(self, genome):
        self.genome = genome

    def evaluate(
            self, 
            input_value: float,
        ) -> dict[Action, float]:
        activations = {}
        

        for action, weight in self.genome.weights.items():
            activations[action] = input_value * weight
            
        return activations

    def choose_action(
            self, 
            input_value: float,
            random_generator: random.Random,
    ) -> tuple[Action, dict[Action, float]]:
        activations = self.evaluate(input_value)
        highest_activation = max(activations.values())
        

        tied_actions = [
            action
            for action, activation in activations.items() 
            if activation == highest_activation
            ]

        chosen_action = random_generator.choice(tied_actions)
        
        return chosen_action, activations
        