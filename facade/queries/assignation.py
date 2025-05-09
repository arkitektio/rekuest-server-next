from facade import models, scalars, types
from kante.types import Info
from authentikate.vars import get_user, get_client


def assignations(
    info: Info,
    instance_id: scalars.InstanceID | None = None,
) -> list[types.Assignation]:
    

    registry, _ = models.Registry.objects.get_or_create(
        client=info.context.request.client, user=info.context.request.user
    )

    waiter, _ = models.Waiter.objects.get_or_create(
        registry=registry, instance_id=instance_id, defaults=dict(name="default")
    )

    return (
        models.Assignation.objects.filter(reservation__waiter=waiter)
        .order_by("created_at")
        .all()
    )
