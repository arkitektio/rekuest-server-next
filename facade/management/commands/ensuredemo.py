from django.core.management.base import BaseCommand
from django.conf import settings
from facade.models import Node
from rekuest_core.inputs import models
from facade.unique import calculate_node_hash, infer_node_scope

def create_n_empty_streams(n):
    return [list() for i in range(n)]



definitions = [
    models.DefinitionInputModel(
        name="Add",
        kind="FUNCTION",
        description="Adds two numbers",
        args=[models.PortInputModel(
            key="a", scope="GLOBAL", kind="INT", nullable=False, effects=[]), models.PortInputModel(key="b", scope="GLOBAL", kind="FLOAT", nullable=False, effects=[])],
        returns=[models.PortInputModel(key="sum", scope="GLOBAL", kind="FLOAT", nullable=False, effects=[])],
        port_groups=[models.PortGroupInputModel(key="default", hidden=False)]
    ),
    models.DefinitionInputModel(
        name="Subtract",
        kind="FUNCTION",
        description="Subtracts two numbers",
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
        description="Subtracts two numbers",
        args=[models.PortInputModel(
            key="a", scope="GLOBAL", kind="INT", nullable=False, effects=[], validators=[models.ValidatorInputModel(function="(value, otherValues) =>  value > 4 || 'Fuck you' ")]), models.PortInputModel(key="b", scope="GLOBAL", kind="FLOAT", nullable=False, effects=[], validators=[models.ValidatorInputModel(function="(value, a) =>  value > a || 'Needs to be bigger than a' ", dependencies=["a"])])],
        returns=[models.PortInputModel(key="difference", scope="GLOBAL", kind="FLOAT", nullable=False, effects=[])],
        port_groups=[models.PortGroupInputModel(key="default", hidden=False)]
    ),
]





class Command(BaseCommand):
    help = "Creates all of the reactive nodes"

    def handle(self, *args, **kwargs):




        for definition in definitions:

            hash = calculate_node_hash(definition)
            scope = infer_node_scope(definition)

        
            node, c = Node.objects.update_or_create(
                hash=hash,
                defaults=dict(
                    description=definition.description or "No description",
                    args=[i.dict() for i in definition.args],
                    scope=scope,
                    kind=definition.kind,
                    port_groups=[i.dict() for i in definition.port_groups],
                    returns=[i.dict() for i in definition.returns],
                    name=definition.name,
                )
            )

            if c:



                print(f"Created node {node.name}")

            else:
                print(f"Updated node {node.name}")

