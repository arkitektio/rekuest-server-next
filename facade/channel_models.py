from pydantic import BaseModel, Field



class DBEvent(BaseModel):
    """A model representing a database event."""

    event_type: str = Field(..., description="Type of the event (e.g., 'insert', 'update', 'delete').")
    
    
    
class StateUpdateEvent(BaseModel):
    """A model representing a state update event."""
    state: str = Field(..., description="The state that was updated.")
    
    
class AssignationEventCreatedEvent(BaseModel):
    """A model representing an event update."""
    event: str = Field(..., description="The event that was created.")