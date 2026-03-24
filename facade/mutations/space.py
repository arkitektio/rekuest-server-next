from kante.types import Info
from facade import types, models, inputs, enums
import uuid
import strawberry


def create_space(info: Info, input: inputs.CreateSpaceInput) -> types.Space:
    x, _ = models.Space.objects.update_or_create(
        name=input.key,
        organization=info.context.request.organization,
        defaults=dict(
            key=input.key,
            creator=info.context.request.user,
        ),
    )
    return x


def create_space_membership(info: Info, input: inputs.CreateSpaceMembershipInput) -> types.SpaceMembership:
    space = models.Space.objects.get(id=input.space_id)
    agent = models.Agent.objects.get(id=input.agent_id)

    membership, _ = models.SpaceMembership.objects.update_or_create(
        space=space,
        agent=agent,
        defaults=dict(
            role="just a member",
        ),
    )

    return membership
