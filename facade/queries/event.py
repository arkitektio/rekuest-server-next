from typing import List

import strawberry
from facade import filters, models, scalars, types
from kante.types import Info


def event(
    info: Info,
    id: strawberry.ID | None = None,
) -> list[types.AssignationEvent]:
    return models.AssignationEvent.objects.get(id=id)
