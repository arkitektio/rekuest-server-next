from facade import models, scalars, types
from kante.types import Info
from authentikate.vars import get_user, get_client


def assignations(
    info: Info,
    instance_id: scalars.InstanceID | None = None,
) -> list[types.Assignation]:
    
    user = get_user()
    client = get_client()

    registry, _ = models.Registry.objects.get_or_create(
        client=client, user=user
    )

    waiter, _ = models.Waiter.objects.get_or_create(
        registry=registry, instance_id=instance_id, defaults=dict(name="default")
    )

    return (
        models.Assignation.objects.filter(reservation__waiter=waiter)
        .order_by("created_at")
        .all()
    )
