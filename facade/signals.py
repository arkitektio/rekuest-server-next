from django.db.models.signals import post_save
from django.dispatch import receiver
from facade import models
from facade.channels import node_created_broadcast, agent_updated_broadcast
import logging
from guardian.shortcuts import assign_perm
from facade.consumers.async_consumer import AgentConsumer


logger = logging.getLogger(__name__)
logger.info("Loading signals")

@receiver(post_save, sender=models.Node)
def node_singal(sender, instance=None, **kwargs):
    print("Signal received!")
    if instance:
        node_created_broadcast(instance.id, [f"nodes"])



@receiver(post_save, sender=models.Reservation)
def reservation_signal(sender, instance=None, **kwargs):
    print("Signal received!")
    logger.info("Reservation received!")

@receiver(post_save, sender=models.Provision)
def provision_signal(sender, instance=None, **kwargs):
    logger.info("Reservation received!")


@receiver(post_save, sender=models.Template)
def template_post_save(sender, instance: models.Template =None, created=None, **kwargs):
    assign_perm("providable", instance.agent.registry.user, instance)

@receiver(post_save, sender=models.Provision)
def prov_post_save(sender, instance: models.Provision = None, created=None, **kwargs):

    if instance:
        print("Provision saved!")
        AgentConsumer.broadcast(instance.agent.id, {"type": "provision", "id": instance.id})

    if created:
        assign_perm("can_link_to", instance.agent.registry.user, instance)




    


@receiver(post_save, sender=models.Agent)
def agent_post_save(sender, instance: models.Agent = None, created=None, **kwargs):

    if instance:
        agent_updated_broadcast(instance.id, [f"agents"])