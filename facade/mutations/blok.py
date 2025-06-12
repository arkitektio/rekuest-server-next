from kante.types import Info
from facade import types, models, inputs, enums
import uuid
import strawberry








def create_blok(info: Info, input: inputs.CreateBlokInput) -> types.Blok:
    
    x, _ = models.Blok.objects.update_or_create(
        name=input.name,
        defaults=dict(
            action_demands=[strawberry.asdict(x) for x in input.action_demands],
            state_demands=[strawberry.asdict(x) for x in input.state_demands],
            description=input.description,
            creator=info.context.request.user,
            url=input.url,
        )
    )

    return x
