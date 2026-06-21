"""Inputs for agent lifecycle controls (pin, bounce, kick, block, update)."""

import strawberry
from pydantic import BaseModel, Field
from strawberry.experimental import pydantic


class PinInputModel(BaseModel):
    """Base model for pinning input data.

    Attributes:
        id: The unique identifier of the item to pin
        pin: Boolean flag indicating whether to pin or unpin
    """

    id: str = Field(description="The unique identifier of the item to pin.")
    pin: bool = Field(description="Boolean flag indicating whether to pin or unpin.")


@pydantic.input(PinInputModel, description="The input for pinning an model.")
class PinInput:
    id: strawberry.ID
    pin: bool


class BounceInputModel(BaseModel):
    """Base model for bouncing an agent.

    Attributes:
        agent: ID of the agent to bounce
    """

    agent: str = Field(description="The agent ID to bounce.")


@pydantic.input(BounceInputModel, description="The input for bouncing an agent.")
class BounceInput:
    agent: strawberry.ID


class KickInputModel(BaseModel):
    """Base model for bouncing an agent.

    Attributes:
        agent: ID of the agent to bounce
    """

    agent: str = Field(description="The agent ID to bounce.")
    reason: str | None = Field(default=None, description="The reason for kicking the agent.")


@pydantic.input(KickInputModel, description="The input for bouncing an agent.")
class KickInput:
    agent: strawberry.ID
    reason: str | None = None


class BlockInputModel(BaseModel):
    """Base model for bouncing an agent.

    Attributes:
        agent: ID of the agent to bounce
    """

    agent: str = Field(description="The agent ID to bounce.")
    reason: str | None = Field(default=None, description="The reason for kicking the agent.")


@pydantic.input(BlockInputModel, description="The input for bouncing an agent.")
class BlockInput:
    agent: strawberry.ID
    reason: str | None = None


class UnblockInputModel(BaseModel):
    """Base model for bouncing an agent.

    Attributes:
        agent: ID of the agent to bounce
    """

    agent: str = Field(description="The agent ID to unblock.")


@pydantic.input(UnblockInputModel, description="The input for bouncing an agent.")
class UnblockInput:
    agent: strawberry.ID


class UpdateAgentInputModel(BaseModel):
    """Base model for updating an agent.

    Attributes:
        id: The unique identifier of the agent to update
        name: The new name for the agent
    """

    id: str = Field(description="The ID of the agent to update.")
    name: str | None = Field(default=None, description="The new name for the agent.")


@pydantic.input(UpdateAgentInputModel, description="The input for updating an agent.")
class UpdateAgentInput:
    id: strawberry.ID
    name: str | None = None
