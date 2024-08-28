from typing import List
from facade import filters, models, scalars, types
from kante.types import Info

def assignations(
    info: Info,
    instance_id: scalars.InstanceID | None = None,
) -> list[types.Assignation]:
    
    registry, _ = models.Registry.objects.get_or_create(
        app=info.context.request.app, user=info.context.request.user
    )

    waiter, _ = models.Waiter.objects.get_or_create(
        registry=registry, instance_id=instance_id, defaults=dict(name="default")
    )

    return models.Assignation.objects.filter(reservation__waiter=waiter).order_by("created_at").all()