from reaktion.models import ReactiveTemplate
from django.core.management.base import BaseCommand
from django.conf import settings
from reaktion.inputs import ReactiveTemplateInputModel
from reaktion import enums
from facade.inputs import PortInputModel


def create_n_empty_streams(n):
    return [list() for i in range(n)]


class Command(BaseCommand):
    help = "Creates all of the reactive nodes"

    def handle(self, *args, **kwargs):
        reactive_nodes = [
            ReactiveTemplateInputModel(
                title="Zip",
                description="Zip two streams together",
                ins=create_n_empty_streams(2),
                outs=create_n_empty_streams(1),
                constants=[],
                implementation=enums.ReactiveImplementation.ZIP,
            )
        ]

        for node in reactive_nodes:
            serialized = node.dict()
            r, _ = ReactiveTemplate.objects.update_or_create(
                title=node.title,
                description=node.description,
                defaults=dict(
                    outs=serialized["outs"],
                    constants=serialized["constants"],
                    implementation=node.implementation,
                    ins=serialized["ins"],
                ),
            )
