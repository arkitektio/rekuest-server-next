from django.core.management.base import BaseCommand
from django.conf import settings
from facade import models, inputs
from facade.unique import calculate_node_hash, infer_node_scope

def create_n_empty_streams(n):
    return [list() for i in range(n)]



definitions = [
    inputs.DefinitionInputModel(
        name="Add",
        kind="FUNCTION",
        description="Adds two numbers",
        args=[inputs.PortInputModel(
            key="a", scope="GLOBAL", kind="INT", nullable=False, effects=[]), inputs.PortInputModel(key="b", scope="GLOBAL", kind="FLOAT", nullable=False, effects=[])],
        returns=[inputs.PortInputModel(key="sum", scope="GLOBAL", kind="FLOAT", nullable=False, effects=[])],
        port_groups=[inputs.PortGroupInputModel(key="default", hidden=False)]
    ),
    inputs.DefinitionInputModel(
        name="Subtract",
        kind="FUNCTION",
        description="Subtracts two numbers",
        args=[inputs.PortInputModel(
            key="a", scope="GLOBAL", kind="INT", nullable=False, effects=[]), inputs.PortInputModel(key="b", scope="GLOBAL", kind="FLOAT", nullable=False, effects=[], validators=[])],
        returns=[inputs.PortInputModel(key="difference", scope="GLOBAL", kind="FLOAT", nullable=False, effects=[])],
        port_groups=[inputs.PortGroupInputModel(key="default", hidden=False)]
    ),
    inputs.DefinitionInputModel(
        name="Franko",
        kind="FUNCTION",
        description="Subtracts two numbers",
        args=[inputs.PortInputModel(
            key="a", scope="GLOBAL", kind="INT", nullable=False, effects=[]), inputs.PortInputModel(key="b", scope="GLOBAL", kind="FLOAT", nullable=False, effects=[], validators=["(value, otherValues) => { if (value < 0) return 'Value must be positive'; }"])],
        returns=[inputs.PortInputModel(key="difference", scope="GLOBAL", kind="FLOAT", nullable=False, effects=[])],
        port_groups=[inputs.PortGroupInputModel(key="default", hidden=False)]
    ),
    inputs.DefinitionInputModel(
        name="Intense Validator",
        kind="FUNCTION",
        description="Subtracts two numbers",
        args=[inputs.PortInputModel(
            key="a", scope="GLOBAL", kind="INT", nullable=False, effects=[], validators=["(value, otherValues) =>  value > 4 || 'Fuck you' "]), inputs.PortInputModel(key="b", scope="GLOBAL", kind="FLOAT", nullable=False, effects=[], validators=["(value, otherValues) => { if (value < 0) return 'Value must be positive'; }"])],
        returns=[inputs.PortInputModel(key="difference", scope="GLOBAL", kind="FLOAT", nullable=False, effects=[])],
        port_groups=[inputs.PortGroupInputModel(key="default", hidden=False)]
    ),
]





class Command(BaseCommand):
    help = "Creates all of the reactive nodes"

    def handle(self, *args, **kwargs):




        for definition in definitions:

            hash = calculate_node_hash(definition)
            scope = infer_node_scope(definition)

        
            node, c = models.Node.objects.update_or_create(
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

