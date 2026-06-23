from kante.channel import build_channel
from .channel_events import StateUpdateEvent, DBEvent, TaskEventCreatedEvent, ImplementationEvent, AgentEvent, ChildTaskEvent, PatchEvent


action_channel = build_channel(DBEvent, "action_created_broadcast")

agent_updated_channel = build_channel(AgentEvent, "agent_updated_broadcast")

task_updated_channel = build_channel(DBEvent, "task_broadcast")
task_event_channel = build_channel(TaskEventCreatedEvent)

child_task_channel = build_channel(ChildTaskEvent)


new_implementation_channel = build_channel(ImplementationEvent)


patch_channel = build_channel(PatchEvent)

state_update_channel = build_channel(StateUpdateEvent)
