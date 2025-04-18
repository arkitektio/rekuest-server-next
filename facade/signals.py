from django.db.models.signals import post_save, pre_delete, post_delete
from django.dispatch import receiver
from facade import models
from facade.channels import (
    node_created_broadcast,
    agent_updated_broadcast,
    provision_event_broadcast,
    reservation_event_broadcast,
    assignation_broadcast,
    reservation_broadcast,
    template_broadcast,
)
import logging
from guardian.shortcuts import assign_perm


logger = logging.getLogger(__name__)
logger.info("Loading sssignals")


@receiver(post_save, sender=models.Node)
def node_singal(sender, instance=None, **kwargs):
    if instance:
        node_created_broadcast(instance.id, [f"nodes"])


@receiver(post_save, sender=models.Reservation)
def reservation_signal(sender, instance=None, **kwargs):
    logger.info("Reservation received!")


@receiver(post_save, sender=models.Template)
def template_post_save(
    sender, instance: models.Template = None, created=None, **kwargs
):
    assign_perm("providable", instance.agent.registry.user, instance)
    template_broadcast(
        {"id": instance.id, "type": "create" if created else "update"},
        [f"agent_{instance.agent.id}"],
    )



@receiver(post_save, sender=models.Agent)
def agent_post_save(sender, instance: models.Agent = None, created=None, **kwargs):
    if instance:
       print("Agent post save")
       agent_updated_broadcast(
            {"id": instance.id, "type": "create" if created else "update"},
            [f"agents_for_{instance.registry.user.id}"],
        )

@receiver(post_save, sender=models.Assignation)
def ass_post_save(sender, instance: models.Assignation = None, created=None, **kwargs):
    if created:
        assignation_broadcast(
            {"id": instance.id, "type": "created"}, [f"ass_waiter_{instance.waiter.id}"]
        )


@receiver(post_save, sender=models.AssignationEvent)
def ass_event_post_save(
    sender, instance: models.AssignationEvent = None, created=None, **kwargs
):
    assignation_broadcast(
        {"id": instance.id, "type": "event"},
        [f"ass_waiter_{instance.assignation.waiter.id}"],
    )


@receiver(post_save, sender=models.Reservation)
def res_post_save(sender, instance: models.Reservation = None, created=None, **kwargs):
    if created:
        pass
        # reservation_broadcast(instance.id, [f"res_waiter_{instance.waiter.id}"])


@receiver(post_save, sender=models.Template)
def temp_post_save(sender, instance: models.Template = None, **kwargs):
    template_broadcast(instance.id, [f"template_{instance.id}"])


@receiver(post_delete, sender=models.Template)
def temp_post_save(sender, instance: models.Template = None, **kwargs):
    pass
