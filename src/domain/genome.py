from domain.action import Action

class Genome:
    def __init__(self):
        self.weights = {
            Action.WAIT: 0.1,
            Action.MOVE_FORWARD: 0.2,
            Action.TURN_LEFT: -0.1,
            Action.TURN_RIGHT: 0.0,
            Action.EAT: 0.8,
        }