from kante.types import Info
from facade import types, models, inputs, enums, logic
import uuid
import strawberry


def auto_resolve(info: Info, input: inputs.AutoResolveInput) -> types.Resolution:
    implementation = models.Implementation.objects.get(id=input.implementation)
    resolution = models.Resolution.objects.create(
        name=f"Auto-resolve for {implementation.name}",
        creator=info.context.request.user,
        organization=info.context.request.organization,
        implementation=implementation,
    )

    logic.auto_resolve(info, implementation, resolution)
    return resolution


def create_resolution(info: Info, input: inputs.CreateResolutionInput) -> types.Resolution:
    x, _ = models.Blok.objects.update_or_create(
        name=input.name,
        defaults=dict(
            action_demands=[strawberry.asdict(x) for x in input.action_demands],
            state_demands=[strawberry.asdict(x) for x in input.state_demands],
            description=input.description,
            creator=info.context.request.user,
            url=input.url,
        ),
    )

    return x
