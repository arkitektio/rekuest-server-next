from kante.types import Info
from facade import types, models, inputs, enums
import uuid
import strawberry
from datalayer.models import MediaStore


def create_threed_model(info: Info, input: inputs.CreateThreeDModelInput) -> types.ThreeDModel:
    file = MediaStore.objects.get(id=input.media)
    x = models.ThreeDModel.objects.create(
        name=input.name,
        description=input.description,
        file=file,
    )
    return x


def update_threed_model(info: Info, input: inputs.UpdateThreeDModelInput) -> types.ThreeDModel:
    x = models.ThreeDModel.objects.get(id=input.id)
    if input.name is not None:
        x.name = input.name
    if input.description is not None:
        x.description = input.description
    if input.media is not None:
        x.file = MediaStore.objects.get(id=input.media)
    x.save()
    return x


def delete_threed_model(info: Info, input: inputs.DeleteThreeDModelInput) -> strawberry.ID:
    x = models.ThreeDModel.objects.get(id=input.id)
    x.delete()
    return input.id
