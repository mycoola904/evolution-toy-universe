from domain.action import Action
import random

class Genome:
    def __init__(
            self,
            weights: dict[Action, float] | None = None,
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
            action: random_generator.uniform(
                minimum_weight,
                maximum_weight
            )
            for action in Action
        }
        return cls(weights=weights)        
