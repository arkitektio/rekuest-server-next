from kante.channel import build_channel
from .channel_events import StateUpdateEvent, DBEvent, AssignationEventCreatedEvent, ImplementationEvent, AgentEvent, ChildAssignationEvent, PatchEvent


action_channel = build_channel(DBEvent, "action_created_broadcast")

agent_updated_channel = build_channel(AgentEvent, "agent_updated_broadcast")

assignation_updated_channel = build_channel(DBEvent, "assignation_broadcast")
assignation_event_channel = build_channel(AssignationEventCreatedEvent)

child_assignation_channel = build_channel(ChildAssignationEvent)


new_implementation_channel = build_channel(ImplementationEvent)


patch_channel = build_channel(PatchEvent)

state_update_channel = build_channel(StateUpdateEvent)
