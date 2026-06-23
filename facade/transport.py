"""The one place that knows *how to reach* a participant.

Two best-effort notifiers over the authoritative DB rows:

- :func:`deliver_to_agent` — a single ToAgent command to one agent: redis queue for a
  WEBSOCKET agent, HMAC-signed POST for a WEBHOOK HookAgent.
- :func:`publish_task_event` — fan a persisted ``TaskEvent`` out to its
  caller: the channel layer (GraphQL subscription + live WS forward) and, if the caller is a
  HookAgent, a webhook POST.

Both run only AFTER the relevant row is persisted, so a failed notification is recoverable
from the DB — the real-time layer never has to be reliable, only prompt.
"""

from __future__ import annotations

import logging

from facade import caller_events, channel_events, channels, enums, hooks, messages, models
from facade.consumers.agent_queue import RedisAgentQueue

logger = logging.getLogger(__name__)


def deliver_to_agent(agent: models.Agent, message: messages.ToAgentMessage) -> None:
    """Send one ToAgent message to ``agent`` over its transport (queue or webhook)."""
    body = message.model_dump_json()
    if agent.kind == enums.AgentKind.WEBHOOK.value:
        hooks.deliver_to_hook(agent, body)
    else:
        RedisAgentQueue.from_settings().push(str(agent.pk), body)


def publish_task_event(event: models.TaskEvent) -> None:
    """Fan a persisted task event out to its caller (channel layer + webhook)."""
    task = event.task
    caller_id = task.caller_id
    if not caller_id:
        return
    # Live WS forward + GraphQL subscription consume this channel-layer broadcast.
    channels.task_event_channel.broadcast(
        channel_events.TaskEventCreatedEvent(event=event.id),  # pyright: ignore[reportCallIssue]  # pydantic Field(None) default
        [f"task_caller_{caller_id}"],
    )
    _deliver_caller_event_to_webhook(event, task)


def _deliver_caller_event_to_webhook(event: models.TaskEvent, task: models.Task) -> None:
    """If the task's caller is a HookAgent, POST the …Event mirror to its hook_url."""
    caller = task.caller
    if caller is None:
        return
    agent = (
        models.Agent.objects.filter(
            client_id=caller.client_id,
            user_id=caller.user_id,
            organization_id=caller.organization_id,
            kind=enums.AgentKind.WEBHOOK.value,
        )
        .exclude(hook_url__isnull=True)
        .exclude(hook_url="")
        .first()
    )
    if agent is None:
        return
    # A Django model satisfies EventLike at runtime, but pyright can't see through the
    # TextChoicesField descriptor to verify it structurally (needs a mypy plugin).
    message = caller_events.build_execution_event(event)  # pyright: ignore[reportArgumentType]
    if message is not None:
        hooks.deliver_to_hook(agent, message.model_dump_json())
