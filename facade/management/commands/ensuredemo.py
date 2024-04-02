from django.core.management.base import BaseCommand
from django.conf import settings
from facade.models import Node
from rekuest_core.inputs import models
from facade.unique import calculate_node_hash, infer_node_scope
from facade.creation import create_node_from_definition

def create_n_empty_streams(n):
    return [list() for i in range(n)]



definitions = [
    models.DefinitionInputModel(
        name="Add",
        kind="FUNCTION",
        description="Calculate {{a}} + {{b}}",
        args=[models.PortInputModel(
            key="a", scope="GLOBAL", kind="INT", nullable=False, effects=[]), models.PortInputModel(key="b", scope="GLOBAL", kind="FLOAT", nullable=False, effects=[])],
        returns=[models.PortInputModel(key="sum", scope="GLOBAL", kind="FLOAT", nullable=False, effects=[])],
        port_groups=[models.PortGroupInputModel(key="default", hidden=False)]
    ),
    models.DefinitionInputModel(
        name="Subtract",
        kind="FUNCTION",
        description="Calculate {{a}} - {{b}}",
        args=[models.PortInputModel(
            key="a", scope="GLOBAL", kind="INT", nullable=False, effects=[]), models.PortInputModel(key="b", scope="GLOBAL", kind="FLOAT", nullable=False, effects=[], validators=[])],
        returns=[models.PortInputModel(key="difference", scope="GLOBAL", kind="FLOAT", nullable=False, effects=[])],
        port_groups=[models.PortGroupInputModel(key="default", hidden=False)]
    ),
    models.DefinitionInputModel(
        name="Franko",
        kind="FUNCTION",
        description="Subtracts two numbers",
        args=[models.PortInputModel(
            key="a", scope="GLOBAL", kind="INT", nullable=False, effects=[]), models.PortInputModel(key="b", scope="GLOBAL", kind="FLOAT", nullable=False, effects=[])],
        returns=[models.PortInputModel(key="difference", scope="GLOBAL", kind="FLOAT", nullable=False, effects=[])],
        port_groups=[models.PortGroupInputModel(key="default", hidden=False)]
    ),
    models.DefinitionInputModel(
        name="Intense Validator",
        kind="FUNCTION",
        description="Subtracts {two numbers}",
        args=[models.PortInputModel(
            key="a", scope="GLOBAL", kind="INT", nullable=False, effects=[], validators=[models.ValidatorInputModel(function="(value, b) =>  value > b || 'Needs to be bigger than b' ", dependencies=["b"])]), models.PortInputModel(key="b", scope="GLOBAL", kind="FLOAT", nullable=False, effects=[])],
        returns=[models.PortInputModel(key="difference", scope="GLOBAL", kind="FLOAT", nullable=False, effects=[])],
        port_groups=[models.PortGroupInputModel(key="default", hidden=False)]
    ),
    models.DefinitionInputModel(
        name="Is Bigger",
        kind="FUNCTION",
        description="Checks if {{a}} is bigger than {{b}}",
        args=[models.PortInputModel(
            key="a", scope="GLOBAL", kind="INT", nullable=False, effects=[]),
            models.PortInputModel(
            key="b", scope="GLOBAL", kind="INT", nullable=True, effects=[], default=3)],
        returns=[models.PortInputModel(key="bigger", scope="GLOBAL", kind="BOOL", nullable=False, effects=[])],
        port_groups=[models.PortGroupInputModel(key="default", hidden=False)]
    ),
]





class Command(BaseCommand):
    help = "Creates all of the reactive nodes"

    def handle(self, *args, **kwargs):




        for definition in definitions:

            create_node_from_definition(definition)

