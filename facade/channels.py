from kante.channel import build_channel
from .channel_events import StateUpdateEvent, DBEvent, AssignationEventCreatedEvent, ImplementationSignal, AgentSignal


action_channel  = build_channel(
    DBEvent, "action_created_broadcast"
)

agent_updated_channel = build_channel(AgentSignal,"agent_updated_broadcast")

assignation_updated_channel = build_channel(DBEvent,"assignation_broadcast")
assignation_event_channel = build_channel(AssignationEventCreatedEvent)



new_implementation_channel  = build_channel(
    ImplementationSignal
)


state_update_channel = build_channel(
    DBEvent,"state_update_event_broadcast"
)



reservation_channel = build_channel(
    DBEvent,"reservation_event_broadcast"
)


state_update_channel = build_channel(StateUpdateEvent)
