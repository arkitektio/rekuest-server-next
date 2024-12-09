from kante.types import Info
import strawberry_django
import strawberry
from facade import types, models
from typing import AsyncGenerator
from facade.channels import template_listen


@strawberry.type
class TemplateUpdate:
    create: types.Template
    update: types.Template
    delete: strawberry.ID


async def templates(
    self,
    info: Info,
    agent: strawberry.ID,
) -> AsyncGenerator[TemplateUpdate, None]:
    """Join and subscribe to message sent to the given rooms."""
    async for message in template_listen(info, [f"agent_{agent}"]):
        if message["type"] == "create":
            yield await models.Template.objects.aget(id=message["id"])
        elif message["type"] == "update":
            yield await models.Template.objects.aget(id=message["id"])
        elif message["type"] == "delete":
            yield message["id"]


async def template_change(
    self,
    info: Info,
    template: strawberry.ID,
) -> AsyncGenerator[types.Template, None]:
    """Join and subscribe to message sent to the given rooms."""
    x = await models.Template.objects.aget(id=template)

    async for message in template_listen(info, [f"template_{x.id}"]):
        yield await models.Template.objects.aget(id=message)
