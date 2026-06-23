from pydantic import BaseModel, Field


class DBEvent(BaseModel):
    """A model representing a database event."""

    event_type: str = Field(..., description="Type of the event (e.g., 'insert', 'update', 'delete').")


class StateUpdateEvent(BaseModel):
    """A model representing a state update event."""

    state: int = Field(..., description="The state that was updated.")


class PatchEvent(BaseModel):
    """A model representing a patch event."""

    create: int = Field(..., description="The patch ID that was created.")
    state: int = Field(..., description="The state ID related to the patch.")
    agent: int | None = Field(None, description="The agent ID related to the patch.")


class TaskEventCreatedEvent(BaseModel):
    """A model representing an task event created."""

    event: int | None = Field(None, description="The event that was created.")
    create: int | None = Field(None, description="The task created.")


class ChildTaskEvent(BaseModel):
    """A model representing a child task event."""

    create: int | None = Field(None, description="The task that was created.")
    update: int | None = Field(None, description="The task that was updated.")


class AgentEvent(BaseModel):
    """A model representing an agent event."""

    create: int | None = Field(None, description="The agent that was created.")
    update: int | None = Field(None, description="The agent that was updated.")
    delete: int | None = Field(None, description="The agent that was deleted.")


class ImplementationEvent(BaseModel):
    """A model representing a template event."""

    create: int | None = Field(None, description="The template that was created.")
    update: int | None = Field(None, description="The template that was updated.")
    delete: int | None = Field(None, description="The template that was deleted.")


class ActionEvent(BaseModel):
    """A model representing an action event."""

    create: int | None = Field(None, description="The action that was created.")
    update: int | None = Field(None, description="The action that was updated.")
    delete: int | None = Field(None, description="The action that was deleted.")
