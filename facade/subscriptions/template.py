from kante.types import Info
import strawberry_django
import strawberry
from facade import types, models
from typing import AsyncGenerator
from facade.channels import template_listen




async def template_change(
    self,
    info: Info,
    template: strawberry.ID,
) -> AsyncGenerator[types.Template, None]:
    """Join and subscribe to message sent to the given rooms."""
    x = await models.Template.objects.aget(id=template)

    async for message in template_listen(info, [f"template_{x.id}"]):
        yield await models.Template.objects.aget(id=message)


