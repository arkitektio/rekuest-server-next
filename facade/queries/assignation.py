from facade import models, types
from kante.types import Info
from authentikate.vars import get_user, get_client


def assignations(
    info: Info,
) -> list[types.Assignation]:
    registry, _ = models.Registry.objects.get_or_create(client=info.context.request.client, user=info.context.request.user, organization=info.context.request.organization)

    return models.Assignation.objects.filter(registry=registry).order_by("created_at").all()
