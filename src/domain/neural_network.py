import random


from domain.action import Action
from domain.sensor import Sensor

class NeuralNetwork:
    def __init__(self, genome):
        self.genome = genome

    def evaluate(
        self,
        sensor_values: dict[Sensor, float],
    ) -> dict[Action, float]:
        activations = {}

        for action, sensor_weights in self.genome.weights.items():
            activation = 0.0

            for sensor, weight in sensor_weights.items():
                activation += sensor_values[sensor] * weight

            activations[action] = activation

        return activations

    def choose_action(
            self, 
            sensor_values: dict[Sensor, float],
            random_generator: random.Random,
    ) -> tuple[Action, dict[Action, float]]:
        activations = self.evaluate(sensor_values)

        highest_activation = max(activations.values())
        

        tied_actions = [
            action
            for action, activation in activations.items() 
            if activation == highest_activation
            ]

        chosen_action = random_generator.choice(tied_actions)
        
        return chosen_action, activations
        