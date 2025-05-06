from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from facade import models, channels, channel_events
import logging


logger = logging.getLogger(__name__)
logger.info("Loading sssignals")


@receiver(post_save, sender=models.State)
def state_post_save(sender, instance: models.State = None, created=None, **kwargs):
    
    channels.state_update_channel.broadcast(channel_events.StateUpdateEvent(id=instance.id), [instance.id])


@receiver(post_save, sender=models.Action)
def action_singal(sender, instance=None, created=None, **kwargs):
    if instance:
        if created:
            channels.action_channel.broadcast(channel_events.ActionSignal(create=instance.id), ["actions"])
        else:
            channels.action_channel.broadcast(channel_events.ActionSignal(update=instance.id), ["actions"])
        


@receiver(post_save, sender=models.Reservation)
def reservation_signal(sender, instance=None, **kwargs):
    logger.info("Reservation received!")


@receiver(post_save, sender=models.Agent)
def agent_post_save(sender, instance: models.Agent = None, created=None, **kwargs):
    if instance:
        print("Agent post save")
        channels.agent_updated_channel.broadcast(
            channel_events.AgentSignal(create=instance.id) if created else channel_events.AgentSignal(update=instance.id),
            [f"agents_for_{instance.registry.user.id}"],
        )


@receiver(post_save, sender=models.Assignation)
def ass_post_save(sender, instance: models.Assignation = None, created=None, **kwargs):
    if created:
        channels.assignation_event_channel.broadcast(
            channel_events.AssignationEventCreatedEvent(create=str(instance.id)),
            [f"ass_waiter_{instance.waiter.id}"],
        )


@receiver(post_save, sender=models.AssignationEvent)
def ass_event_post_save(
    sender, instance: models.AssignationEvent = None, created=None, **kwargs
):
    logger.info("Assignation Event received")
    channels.assignation_event_channel.broadcast(
        channel_events.AssignationEventCreatedEvent(event=instance.id),
        [f"ass_waiter_{instance.assignation.waiter.id}"],
    )


@receiver(post_save, sender=models.Reservation)
def res_post_save(sender, instance: models.Reservation = None, created=None, **kwargs):
    if created:
        pass
        # reservation_broadcast(instance.id, [f"res_waiter_{instance.waiter.id}"])


@receiver(post_save, sender=models.Implementation)
def implementation_post_save(sender, instance: models.Implementation = None, created=None, **kwargs):
    if created:
        channels.new_implementation_channel.broadcast(channel_events.ImplementationSignal(create=instance.id))
    else:
        channels.new_implementation_channel.broadcast(channel_events.ImplementationSignal(update=instance.id), [f"implementation_{instance.id}"])



@receiver(post_delete, sender=models.Implementation)
def implementation_post_del(sender, instance: models.Implementation = None, **kwargs):
    
    if instance:
        channels.new_implementation_channel.broadcast(channel_events.ImplementationSignal(delete=instance.id), [f"implementation_{instance.id}"])
    
