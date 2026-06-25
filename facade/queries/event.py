import strawberry
from facade import models, types
from kante.types import Info


def event(
    info: Info,
    id: strawberry.ID | None = None,
) -> list[types.TaskEvent]:
    return models.TaskEvent.objects.get(id=id)
