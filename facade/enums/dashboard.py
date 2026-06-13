from enum import Enum

import strawberry
from django.db.models import TextChoices


class PanelKindChoices(TextChoices):
    STATE = "STATE", "State"
    ASSIGN = "ASSIGN", "Assign"
    TEMPLATE = "TEMPLATE", "Implementation"


@strawberry.enum
class PanelKind(str, Enum):
    STATE = "STATE"
    ASSIGN = "ASSIGN"
