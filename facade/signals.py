from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from facade import models
from facade.channels import node_created_broadcast, agent_updated_broadcast, assignation_event_broadcast, provision_event_broadcast, reservation_event_broadcast, assignation_broadcast, reservation_broadcast, template_broadcast
import logging
from guardian.shortcuts import assign_perm


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
def provision_signal(sender, instance=None,  created=None, **kwargs):
    from facade.backend import controll_backend
    logger.info("Provision received!")
    if created:
        controll_backend.provide(instance)
        assign_perm("can_link_to", instance.agent.registry.user, instance)



@receiver(post_save, sender=models.Template)
def template_post_save(sender, instance: models.Template =None, created=None, **kwargs):
    assign_perm("providable", instance.agent.registry.user, instance)



@receiver(pre_delete, sender=models.Provision)
def prov_pre_delete(sender, instance: models.Provision = None, **kwargs):
    from facade.backend import controll_backend
    pass
    controll_backend.unprovide(instance)


    


@receiver(post_save, sender=models.Agent)
def agent_post_save(sender, instance: models.Agent = None, created=None, **kwargs):

    if instance:
        agent_updated_broadcast(instance.id, [f"agents"])


@receiver(post_save, sender=models.Assignation)
def ass_post_save(sender, instance: models.Assignation = None, created=None, **kwargs):
    if created:
        assignation_broadcast({"id": instance.id, "type": "created"}, [f"ass_waiter_{instance.waiter.id}"])
    
@receiver(post_save, sender=models.AssignationEvent)
def ass_event_post_save(sender, instance: models.AssignationEvent = None, created=None, **kwargs):
    assignation_event_broadcast({"id": instance.id, "type": "event"}, [f"ass_waiter_{instance.assignation.waiter.id}"])
    

@receiver(post_save, sender=models.Reservation)
def res_post_save(sender, instance: models.Reservation = None, created=None, **kwargs):

    if created:
        pass
        #reservation_broadcast(instance.id, [f"res_waiter_{instance.waiter.id}"])
    
@receiver(post_save, sender=models.ReservationEvent)
def res_event_post_save(sender, instance: models.ReservationEvent = None, created=None, **kwargs):

    reservation_event_broadcast(instance.id, [f"reservation_{instance.reservation.id}", f"res_waiter_{instance.reservation.waiter.id}"])



@receiver(post_save, sender=models.ProvisionEvent)
def prov_event_post_save(sender, instance: models.Provision = None, **kwargs):
    pass



@receiver(post_save, sender=models.Template)
def temp_post_save(sender, instance: models.Template = None, **kwargs):
    template_broadcast(instance.id, [f"template_{instance.id}"])
