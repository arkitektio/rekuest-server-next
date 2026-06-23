from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from facade import models, channels, channel_events, transport
from authentikate.models import Organization

import logging


logger = logging.getLogger(__name__)
logger.info("Loading sssignals")


@receiver
def organization_post_save(sender, instance: Organization = None, created=None, **kwargs):
    if created:
        print("Creating all the agents for organization:", instance.name)


@receiver(post_save, sender=models.State)
def state_post_save(sender, instance: models.State = None, created=None, **kwargs):
    channels.state_update_channel.broadcast(channel_events.StateUpdateEvent(state=instance.id), [f"state_{instance.id}"])


@receiver(post_save, sender=models.Action)
def action_singal(sender, instance=None, created=None, **kwargs):
    if instance:
        if created:
            channels.action_channel.broadcast(channel_events.ActionEvent(create=instance.id), [f"actions_{instance.organization.id}"])
        else:
            channels.action_channel.broadcast(channel_events.ActionEvent(update=instance.id), [f"actions_{instance.organization.id}"])


@receiver(post_save, sender=models.Agent)
def agent_post_save(sender, instance: models.Agent = None, created=None, **kwargs):
    if instance:
        channels.agent_updated_channel.broadcast(
            channel_events.AgentEvent(create=instance.id) if created else channel_events.AgentEvent(update=instance.id),
            [f"agents_for_{instance.organization.id}"],
        )


@receiver(post_delete, sender=models.Agent)
def agent_post_delete(sender, instance: models.Agent = None, **kwargs):
    if instance:
        channels.agent_updated_channel.broadcast(
            channel_events.AgentEvent(delete=instance.id),
            [f"agents_for_{instance.organization.id}"],
        )


@receiver(post_save, sender=models.Task)
def task_post_save(sender, instance: models.Task = None, created=None, **kwargs):
    if created and instance.caller_id:
        channels.task_event_channel.broadcast(
            channel_events.TaskEventCreatedEvent(create=str(instance.id)),
            [f"task_caller_{instance.caller_id}"],
        )

    if instance.parent:
        if created:
            channels.child_task_channel.broadcast(
                channel_events.ChildTaskEvent(create=str(instance.id)),
                [f"child_tasks_{instance.parent.id}"],
            )
        else:
            channels.child_task_channel.broadcast(
                channel_events.ChildTaskEvent(update=str(instance.id)),
                [f"child_tasks_{instance.parent.id}"],
            )


@receiver(post_save, sender=models.TaskEvent)
def task_event_post_save(sender, instance: models.TaskEvent = None, created=None, **kwargs):
    logger.info("Task Event received")
    # One typed publisher fans the persisted event out to its caller (channel layer for the
    # GraphQL subscription + live WS forward, and a webhook POST for a HookAgent caller).
    transport.publish_task_event(instance)


@receiver(post_save, sender=models.Implementation)
def implementation_post_save(sender, instance: models.Implementation = None, created=None, **kwargs):
    if created:
        channels.new_implementation_channel.broadcast(channel_events.ImplementationEvent(create=instance.id))
    else:
        channels.new_implementation_channel.broadcast(channel_events.ImplementationEvent(update=instance.id), [f"implementation_{instance.id}"])


@receiver(post_delete, sender=models.Implementation)
def implementation_post_del(sender, instance: models.Implementation = None, **kwargs):
    if instance:
        channels.new_implementation_channel.broadcast(channel_events.ImplementationEvent(delete=instance.id), [f"implementation_{instance.id}"])


@receiver(post_save, sender=models.Patch)
def patch_post_save(sender, instance: models.Patch = None, created=None, **kwargs):
    print("Patch post save signal received for patch:", instance)
    if created:
        topics = [f"patches_state_{instance.state.id}"]
        if instance.agent:
            topics.append(f"patches_agent_{instance.agent.id}")

        print("Broadcasting patch event to topics:", topics)

        channels.patch_channel.broadcast(channel_events.PatchEvent(create=instance.id, state=instance.state.id, agent=instance.agent.id if instance.agent else None), topics)
