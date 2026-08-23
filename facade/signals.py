from django.db import transaction
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from facade import models, channels, channel_events, transport
from authentikate.models import Organization

import logging


logger = logging.getLogger(__name__)
logger.info("Loading sssignals")

_UNSET = object()


def _broadcast_on_commit(channel, event, topics=_UNSET):
    """Fan an event out only once the surrounding transaction commits.

    Signals fire while the writing transaction is still open (e.g. the atomic
    ``implement_agent`` reconcile). Broadcasting immediately would publish events for rows
    that may still roll back, and serializes the channel-layer work inside the lock
    window. Outside a transaction ``on_commit`` runs the callback immediately, so
    non-transactional paths are unaffected.
    """
    if topics is _UNSET:
        transaction.on_commit(lambda: channel.broadcast(event))
    else:
        transaction.on_commit(lambda: channel.broadcast(event, topics))


@receiver
def organization_post_save(sender, instance: Organization = None, created=None, **kwargs):
    if created:
        print("Creating all the agents for organization:", instance.name)


@receiver(post_save, sender=models.State)
def state_post_save(sender, instance: models.State = None, created=None, **kwargs):
    _broadcast_on_commit(channels.state_update_channel, channel_events.StateUpdateEvent(state=instance.id), [f"state_{instance.id}"])


@receiver(post_save, sender=models.Action)
def action_singal(sender, instance=None, created=None, **kwargs):
    if instance:
        if created:
            _broadcast_on_commit(channels.action_channel, channel_events.ActionEvent(create=instance.id), [f"actions_{instance.organization.id}"])
        else:
            _broadcast_on_commit(channels.action_channel, channel_events.ActionEvent(update=instance.id), [f"actions_{instance.organization.id}"])


@receiver(post_save, sender=models.Agent)
def agent_post_save(sender, instance: models.Agent = None, created=None, **kwargs):
    if instance:
        _broadcast_on_commit(
            channels.agent_updated_channel,
            channel_events.AgentEvent(create=instance.id) if created else channel_events.AgentEvent(update=instance.id),
            [f"agents_for_{instance.organization.id}"],
        )


@receiver(post_delete, sender=models.Agent)
def agent_post_delete(sender, instance: models.Agent = None, **kwargs):
    if instance:
        _broadcast_on_commit(
            channels.agent_updated_channel,
            channel_events.AgentEvent(delete=instance.id),
            [f"agents_for_{instance.organization.id}"],
        )


@receiver(post_save, sender=models.Task)
def task_post_save(sender, instance: models.Task = None, created=None, **kwargs):
    # Root-task change feed: a freshly created root task is fanned out to both the caller's
    # feed (mytasks) and the org-wide feed (tasks). Child tasks never reach these feeds.
    if created and instance.root_id is None and instance.caller_id:
        _broadcast_on_commit(
            channels.task_event_channel,
            channel_events.TaskEventCreatedEvent(create=str(instance.id)),
            [
                f"root_tasks_caller_{instance.caller_id}",
                f"root_tasks_org_{instance.caller.organization_id}",
            ],
        )

    # Agent feed: any task (root or child) run by an agent is fanned out to that agent's
    # detail-page feed, so the agent's "latest tasks" list updates live on create and on
    # every status/is_done transition (which re-saves the Task row → arrives here as update).
    if instance.agent_id:
        event = channel_events.ChildTaskEvent(create=str(instance.id)) if created else channel_events.ChildTaskEvent(update=str(instance.id))
        _broadcast_on_commit(channels.agent_task_channel, event, [f"agent_tasks_{instance.agent_id}"])

    # Detail feed: notify the direct parent AND the root, so a subscription on the root task
    # sees the whole subtree while an intermediate task still sees its direct children.
    if instance.parent_id:
        topics = {f"child_tasks_{instance.parent_id}"}
        if instance.root_id:
            topics.add(f"child_tasks_{instance.root_id}")
        event = channel_events.ChildTaskEvent(create=str(instance.id)) if created else channel_events.ChildTaskEvent(update=str(instance.id))
        _broadcast_on_commit(channels.child_task_channel, event, list(topics))


@receiver(post_save, sender=models.TaskEvent)
def task_event_post_save(sender, instance: models.TaskEvent = None, created=None, **kwargs):
    logger.info("Task Event received")
    # One typed publisher fans the persisted event out to its caller (channel layer for the
    # GraphQL subscription + live WS forward, and a webhook POST for a HookAgent caller).
    transaction.on_commit(lambda instance=instance: transport.publish_task_event(instance))


@receiver(post_save, sender=models.Implementation)
def implementation_post_save(sender, instance: models.Implementation = None, created=None, **kwargs):
    if created:
        _broadcast_on_commit(channels.new_implementation_channel, channel_events.ImplementationEvent(create=instance.id))
    else:
        _broadcast_on_commit(channels.new_implementation_channel, channel_events.ImplementationEvent(update=instance.id), [f"implementation_{instance.id}"])


@receiver(post_delete, sender=models.Implementation)
def implementation_post_del(sender, instance: models.Implementation = None, **kwargs):
    if instance:
        _broadcast_on_commit(channels.new_implementation_channel, channel_events.ImplementationEvent(delete=instance.id), [f"implementation_{instance.id}"])


@receiver(post_save, sender=models.Patch)
def patch_post_save(sender, instance: models.Patch = None, created=None, **kwargs):
    print("Patch post save signal received for patch:", instance)
    if created:
        topics = [f"patches_state_{instance.state.id}"]
        if instance.agent:
            topics.append(f"patches_agent_{instance.agent.id}")

        print("Broadcasting patch event to topics:", topics)

        _broadcast_on_commit(channels.patch_channel, channel_events.PatchEvent(create=instance.id, state=instance.state.id, agent=instance.agent.id if instance.agent else None), topics)
