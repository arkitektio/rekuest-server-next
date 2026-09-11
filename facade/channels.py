from kante.channel import build_channel
from .channel_events import ActionEvent, StateUpdateEvent, TaskEventCreatedEvent, ImplementationEvent, AgentEvent, ProbeEventBroadcast, ChildTaskEvent, PatchEvent


action_channel = build_channel(ActionEvent, "action_created_broadcast")

agent_updated_channel = build_channel(AgentEvent, "agent_updated_broadcast")

task_event_channel = build_channel(TaskEventCreatedEvent)

# Same payload model, but explicitly distinct names: unnamed same-model channels share a
# message type in kante, so a future group-name overlap would silently cross-feed them.
child_task_channel = build_channel(ChildTaskEvent, "child_task_feed")

agent_task_channel = build_channel(ChildTaskEvent, "agent_task_feed")


new_implementation_channel = build_channel(ImplementationEvent)


patch_channel = build_channel(PatchEvent)

state_update_channel = build_channel(StateUpdateEvent)

probe_event_channel = build_channel(ProbeEventBroadcast, "probe_event_broadcast")
