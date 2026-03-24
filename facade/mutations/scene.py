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


def create_agent_scene(info: Info, input: inputs.CreateAgentSceneInput) -> types.AgentScene:
    threed_model = models.ThreeDModel.objects.get(id=input.model_id)
    agent = models.Agent.objects.get(id=input.agent_id)
    x = models.AgentScene.objects.create(
        model=threed_model,
        agent=agent,
        transfer_function=input.transfer_function,
    )
    return x


def update_agent_scene(info: Info, input: inputs.UpdateAgentSceneInput) -> types.AgentScene:
    x = models.AgentScene.objects.get(id=input.id)
    if input.transfer_function is not None:
        x.transfer_function = input.transfer_function
    if input.model_id is not None:
        x.model = models.ThreeDModel.objects.get(id=input.model_id)
    x.save()
    return x


def delete_agent_scene(info: Info, input: inputs.DeleteAgentSceneInput) -> strawberry.ID:
    x = models.AgentScene.objects.get(id=input.id)
    x.delete()
    return input.id
