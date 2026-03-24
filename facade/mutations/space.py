from kante.types import Info
from facade import types, models, inputs, enums
import uuid
import strawberry


def create_space(info: Info, input: inputs.CreateSpaceInput) -> types.Space:
    x, _ = models.Space.objects.update_or_create(
        name=input.name,
        defaults=dict(
            creator=info.context.request.user,
        ),
    )
    return x


def update_space(info: Info, input: inputs.UpdateSpaceInput) -> types.Space:
    x = models.Space.objects.get(id=input.id)
    if input.name is not None:
        x.name = input.name
    if input.description is not None:
        x.description = input.description
    x.save()
    return x


def delete_space(info: Info, input: inputs.DeleteSpaceInput) -> strawberry.ID:
    x = models.Space.objects.get(id=input.id)
    x.delete()
    return input.id


def create_space_membership(info: Info, input: inputs.CreateSpaceMembershipInput) -> types.SpaceMembership:
    space = models.Space.objects.get(id=input.space_id)
    agent_scene = models.AgentScene.objects.get(id=input.agent_id)

    membership, _ = models.SpaceMembership.objects.update_or_create(
        space=space,
        agent_scene=agent_scene,
        defaults=dict(
            role="just a member",
        ),
    )

    return membership


def update_space_membership(info: Info, input: inputs.UpdateSpaceMembershipInput) -> types.SpaceMembership:
    x = models.SpaceMembership.objects.get(id=input.id)
    if input.role is not None:
        x.role = input.role
    if input.affine_matrix is not None:
        x.affine_matrix = input.affine_matrix
    if input.model is not None:
        x.model = input.model
    x.save()
    return x


def delete_space_membership(info: Info, input: inputs.DeleteSpaceMembershipInput) -> strawberry.ID:
    x = models.SpaceMembership.objects.get(id=input.id)
    x.delete()
    return input.id
