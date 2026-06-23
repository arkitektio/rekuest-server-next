from facade import models, types
from kante.types import Info
from authentikate.vars import get_user, get_client


def tasks(
    info: Info,
) -> list[types.Task]:
    caller, _ = models.Caller.objects.get_or_create(client=info.context.request.client, user=info.context.request.user, organization=info.context.request.organization)

    return models.Task.objects.filter(caller=caller).order_by("created_at").all()
