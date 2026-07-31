from enum import Enum


class Action(Enum):
    WAIT = "WAIT"
    EAT = "EAT"
    MOVE_FORWARD = "MOVE_FORWARD"
    TURN_LEFT = "TURN_LEFT"
    TURN_RIGHT = "TURN_RIGHT"
