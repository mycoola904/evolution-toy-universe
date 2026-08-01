import random
from domain.action import Action
from domain.sensor import Sensor


class Genome:
    def __init__(
            self,
            weights: dict[Action, dict[Sensor, float]],
                ):
        
            self.weights = weights

    @classmethod
    def random_genome(
            cls,
            random_generator: random.Random,
            minimum_weight: float = -1.0,
            maximum_weight: float = 1.0,
        ) -> "Genome":
        weights = {
            action: {
                sensor: random_generator.uniform(
                    minimum_weight,
                    maximum_weight
                )
                for sensor in Sensor
            }
            for action in Action
        }

        return cls(weights=weights)
