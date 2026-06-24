from facade import models, types
from kante.types import Info


def tasks(
    info: Info,
) -> list[types.Task]:
    caller, _ = models.Caller.objects.get_or_create(client=info.context.request.client, user=info.context.request.user, organization=info.context.request.organization)

    return models.Task.objects.filter(caller=caller).order_by("created_at").all()


def my_tasks(
    info: Info,
) -> list[types.Task]:
    """The root tasks this client (caller) created — the query counterpart of the ``mytasks`` subscription."""
    caller, _ = models.Caller.objects.get_or_create(client=info.context.request.client, user=info.context.request.user, organization=info.context.request.organization)

    return models.Task.objects.filter(caller=caller, root__isnull=True).order_by("-created_at")
