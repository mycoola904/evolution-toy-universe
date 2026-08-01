class Genome:
    def __init__(self):
        self.weights = [
            0.1, # WAIT
            0.2, # MOVE_FORWARD
            -0.1, # TURN_LEFT    
            0.0, # TURN_RIGHT
            0.8, # EAT
        ]