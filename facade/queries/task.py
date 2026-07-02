from typing import Optional

from facade import enums, models, scalars, types
from facade.provenance.canonical import args_hash
from kante.types import Info


def reusable_task_for(
    info: Info,
    action_hash: str,
    args: scalars.Args,
) -> Optional[types.Task]:
    """The latest completed run of a PURE action with these exact (canonical) args, or null.

    This is the replay primitive: the server only makes prior results discoverable — whether
    to reference the returned task instead of re-assigning (and any freshness policy) is the
    orchestrating workflow's decision. Non-pure actions always return null; their runs are
    never offered for replay.
    """
    return (
        models.Task.objects.filter(
            action__hash=action_hash,
            action__pure=True,
            action__organization=info.context.request.organization,
            args_hash=args_hash(args or {}),
            is_done=True,
            latest_event_kind=enums.TaskEventKind.COMPLETED,
            ephemeral=False,
        )
        .order_by("-finished_at")
        .first()
    )


def tasks(
    info: Info,
) -> list[types.Task]:
    caller, _ = models.Caller.objects.get_or_create(client=info.context.request.client, user=info.context.request.user, organization=info.context.request.organization)

    return models.Task.objects.filter(caller=caller).order_by("created_at").all()


def my_tasks(
    info: Info,
) -> list[types.Task]:
    """The root tasks this client created and which are NOT done.."""
    caller, _ = models.Caller.objects.get_or_create(client=info.context.request.client, user=info.context.request.user, organization=info.context.request.organization)

    return models.Task.objects.filter(caller=caller, root__isnull=True, is_done=False).order_by("-created_at")
