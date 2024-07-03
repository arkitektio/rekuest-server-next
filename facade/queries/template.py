from typing import List

import strawberry
from facade import filters, models, scalars, types
from kante.types import Info


def template_at(
    info: Info,
    agent: strawberry.ID,
    extension: str,
    interface: str,
) -> types.Template:
    return models.Template.objects.get(agent_id=agent, extension=extension, interface=interface)
