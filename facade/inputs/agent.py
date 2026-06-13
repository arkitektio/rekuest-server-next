"""Inputs for agent lifecycle controls (pin, bounce, kick, block, update)."""

import strawberry
from pydantic import BaseModel
from strawberry.experimental import pydantic


class PinInputModel(BaseModel):
    """Base model for pinning input data.

    Attributes:
        id: The unique identifier of the item to pin
        pin: Boolean flag indicating whether to pin or unpin
    """

    id: str
    pin: bool


@pydantic.input(PinInputModel, description="The input for pinning an model.")
class PinInput:
    id: strawberry.ID
    pin: bool


class BounceInputModel(BaseModel):
    """Base model for bouncing an agent.

    Attributes:
        agent: ID of the agent to bounce
    """

    agent: str


@pydantic.input(BounceInputModel, description="The input for bouncing an agent.")
class BounceInput:
    agent: strawberry.ID = strawberry.field(description="The agent ID to bounce.")


class KickInputModel(BaseModel):
    """Base model for bouncing an agent.

    Attributes:
        agent: ID of the agent to bounce
    """

    agent: str
    reason: str | None = None


@pydantic.input(KickInputModel, description="The input for bouncing an agent.")
class KickInput:
    agent: strawberry.ID = strawberry.field(description="The agent ID to bounce.")
    reason: str | None = strawberry.field(default=None, description="The reason for kicking the agent.")


class BlockInputModel(BaseModel):
    """Base model for bouncing an agent.

    Attributes:
        agent: ID of the agent to bounce
    """

    agent: str
    reason: str | None = None


@pydantic.input(BlockInputModel, description="The input for bouncing an agent.")
class BlockInput:
    agent: strawberry.ID = strawberry.field(description="The agent ID to bounce.")
    reason: str | None = strawberry.field(default=None, description="The reason for kicking the agent.")


class UnblockInputModel(BaseModel):
    """Base model for bouncing an agent.

    Attributes:
        agent: ID of the agent to bounce
    """

    agent: str


@pydantic.input(UnblockInputModel, description="The input for bouncing an agent.")
class UnblockInput:
    agent: strawberry.ID = strawberry.field(description="The agent ID to unblock.")


class UpdateAgentInputModel(BaseModel):
    """Base model for updating an agent.

    Attributes:
        id: The unique identifier of the agent to update
        name: The new name for the agent
    """

    id: str
    name: str | None = None


@pydantic.input(UpdateAgentInputModel, description="The input for updating an agent.")
class UpdateAgentInput:
    id: strawberry.ID = strawberry.field(description="The ID of the agent to update.")
    name: str | None = strawberry.field(default=None, description="The new name for the agent.")
