from pydantic import BaseModel, Field



class DBEvent(BaseModel):
    """A model representing a database event."""

    event_type: str = Field(..., description="Type of the event (e.g., 'insert', 'update', 'delete').")
    
    
    
class StateUpdateEvent(BaseModel):
    """A model representing a state update event."""
    state: str = Field(..., description="The state that was updated.")
    
    
class AssignationEventCreatedEvent(BaseModel):
    """A model representing an assignation event created."""
    event: int | None = Field(None, description="The event that was created.")
    create: int | None = Field(None, description="The assignation created.")
    
    
    
class AgentSignal(BaseModel):
    """A model representing an agent event."""
    create: int | None = Field(None, description="The agent that was created.")
    update: int | None = Field(None, description="The agent that was updated.")
    delete: int | None = Field(None, description="The agent that was deleted.")
    

class ImplementationSignal(BaseModel):
    """A model representing a template event."""
    create: int | None = Field(None, description="The template that was created.")
    update: int | None = Field(None, description="The template that was updated.")
    delete: int | None = Field(None, description="The template that was deleted.")
    
    
class ActionSignal(BaseModel):
    """A model representing an action event."""
    create: int | None = Field(None, description="The action that was created.")
    update: int | None = Field(None, description="The action that was updated.")
    delete: int | None = Field(None, description="The action that was deleted.")