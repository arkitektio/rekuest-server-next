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


def delete_blok(info: Info, input: inputs.DeleteBlokInput) -> bool:

    try:
        blok = models.Blok.objects.get(id=input.id)
        blok.delete()
        return True
    except models.Blok.DoesNotExist:
        return False


def update_blok(info: Info, input: inputs.UpdateBlokInput) -> types.Blok:

    try:
        blok = models.Blok.objects.get(id=input.id)
    except models.Blok.DoesNotExist:
        raise ValueError(f"Blok with id {input.id} does not exist.")

    if input.name is not None:
        blok.name = input.name
    if input.description is not None:
        blok.description = input.description
    if input.components is not None:
        blok.components = [x.model_dump() for x in input.components]
    if input.demo_state is not None:
        blok.demo_state = input.demo_state
    if input.catalog is not None:
        catalog = models.UICatalog.objects.get_or_create(name=input.catalog)[0]
        blok.catalog = catalog

    blok.save()

    if input.dependencies is not None:
        existing_deps = {dep.key: dep for dep in blok.dependencies.all()}
        new_deps = []
        for i in input.dependencies:
            dep, _ = models.BlokDependency.objects.update_or_create(
                blok=blok,
                key=i.key,
                defaults=dict(
                    action_demands=[x.model_dump() for x in i.action_demands] if i.action_demands else [],
                    state_demands=[x.model_dump() for x in i.state_demands] if i.state_demands else [],
                    app_filter=i.app,
                    version_filter=i.version,
                ),
            )
            new_deps.append(dep)
            existing_deps.pop(i.key, None)

        # Delete any dependencies that were not included in the update
        for dep in existing_deps.values():
            dep.delete()

    return blok
