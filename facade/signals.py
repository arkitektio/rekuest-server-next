from django.db.models.signals import post_save
from django.dispatch import receiver
from facade.models import Node
from facade.channels import node_created_broadcast


@receiver(post_save, sender=Node)
def my_handler(sender, instance=None, **kwargs):
    print("Signal received!")
    if instance:
        node_created_broadcast(instance.id, [f"nodes"])
