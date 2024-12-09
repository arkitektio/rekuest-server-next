import strawberry
from enum import Enum


@strawberry.enum
class UIChildKind(str, Enum):
    GRID = "GRID"
    SPLIT = "SPLIT"
    RESERVATION = "RESERVATION"
    STATE = "STATE"
