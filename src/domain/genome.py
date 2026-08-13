import random
from domain.action import Action
from domain.sensor import Sensor


class Genome:
    def __init__(
        self,
        weights: dict[Action, dict[Sensor, float]],
        reproduction_threshold: float,
    ):
        self.weights = weights
        self.reproduction_threshold = reproduction_threshold

    @classmethod
    def random_genome(
        cls,
        random_generator: random.Random,
        reproduction_threshold: float,
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

        return cls(
            weights=weights,
            reproduction_threshold=reproduction_threshold,
        )

    def copy(self) -> "Genome":
        copied_weights = {
            action: sensor_weights.copy()
            for action, sensor_weights in self.weights.items()
        }
        return Genome(
            weights=copied_weights,
            reproduction_threshold=self.reproduction_threshold,
        )

    def to_dict(self) -> dict:
        return {
            "reproduction_threshold": self.reproduction_threshold,
            "weights": {
                action.name: {
                    sensor.name: weight
                    for sensor, weight in sensor_weights.items()
                }
                for action, sensor_weights in self.weights.items()
            },
        }

    def mutated_copy(
        self,
        random_generator: random.Random,
        mutation_rate: float,
        mutation_amount: float,
    ) -> "Genome":
        mutated_weights = {
            action: {
                sensor: (
                    weight
                    + random_generator.uniform(
                        -mutation_amount,
                        mutation_amount,
                    )
                    if random_generator.random() < mutation_rate
                    else weight
                )
                for sensor, weight in sensor_weights.items()
            }
            for action, sensor_weights in self.weights.items()
        }

        return Genome(
            weights=mutated_weights,
            reproduction_threshold=self.reproduction_threshold,
        )
