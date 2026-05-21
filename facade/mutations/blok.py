from kante.types import Info
from facade import types, models, inputs, enums
import uuid
import strawberry


def create_blok(info: Info, input: inputs.CreateBlokInput) -> types.Blok:

    input = input.to_pydantic()

    catalog = models.UICatalog.objects.get_or_create(name=input.catalog)[0] if input.catalog else models.UICatalog.objects.get_or_create(name="default")[0]

    x, _ = models.Blok.objects.update_or_create(
        name=input.name,
        defaults=dict(
            components=[x.model_dump() for x in input.components] if input.components else [],
            description=input.description,
            creator=info.context.request.user,
            catalog=catalog,
            demo_state=input.demo_state,
        ),
    )

    new_deps = []
    if input.dependencies:
        for i in input.dependencies:
            dep, _ = models.BlokDependency.objects.update_or_create(
                blok=x,
                key=i.key,
                defaults=dict(
                    action_demands=[x.model_dump() for x in i.action_demands] if i.action_demands else [],
                    state_demands=[x.model_dump() for x in i.state_demands] if i.state_demands else [],
                    app_filter=i.app,
                    version_filter=i.version,
                ),
            )
            new_deps.append(dep)

    return x
