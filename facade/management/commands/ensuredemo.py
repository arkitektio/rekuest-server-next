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
    models.DefinitionInputModel(
        name="Add",
        kind="FUNCTION",
        description="Adds a {{a}} to {{b}}",
        args=[models.PortInputModel(
            key="a", scope="GLOBAL", kind="INT", nullable=False, effects=[]),
            models.PortInputModel(
            key="b", scope="GLOBAL", kind="INT", nullable=True, effects=[], default=3)],
        returns=[models.PortInputModel(key="bigger", scope="GLOBAL", kind="INT", nullable=False, effects=[])],
        port_groups=[models.PortGroupInputModel(key="default", hidden=False)]
    ),
    models.DefinitionInputModel(
        name="Double",
        kind="FUNCTION",
        description="Double {{a}}",
        args=[models.PortInputModel(
            key="a", scope="GLOBAL", kind="INT", nullable=False, effects=[])],
        returns=[models.PortInputModel(key="bigger", scope="GLOBAL", kind="INT", nullable=False, effects=[])],
        port_groups=[models.PortGroupInputModel(key="default", hidden=False)]
    ),
    models.DefinitionInputModel(
        name="Acquire Image",
        kind="FUNCTION",
        description="Acquires an Z-stack of size {{z}} at the current position",
        args=[models.PortInputModel(
            key="z", scope="GLOBAL", kind="INT", nullable=True, effects=[], default=70)],
        returns=[models.PortInputModel(key="image", scope="GLOBAL", kind="STRUCTURE", identifier="@mikro/image", nullable=False, effects=[])],
        port_groups=[models.PortGroupInputModel(key="default", hidden=False)]
    ),
    models.DefinitionInputModel(
        name="Segment Cells",
        kind="FUNCTION",
        description="Segment the Cells in the image",
        args=[models.PortInputModel(
            key="z", scope="GLOBAL", kind="STRUCTURE", identifier="@mikro/image", nullable=False, effects=[])],
        returns=[models.PortInputModel(key="segmented_image", scope="GLOBAL", kind="STRUCTURE", identifier="@mikro/image", nullable=False, effects=[])],
        port_groups=[models.PortGroupInputModel(key="default", hidden=False)]
    ),
    models.DefinitionInputModel(
        name="Mark Clusters",
        kind="FUNCTION",
        description="Mark Clusters in the Image",
        args=[models.PortInputModel(
            key="z", scope="GLOBAL", kind="STRUCTURE", identifier="@mikro/image")],
        returns=[models.PortInputModel(key="clusters", scope="GLOBAL", kind="LIST", child=models.ChildPortInputModel(kind="STRUCTURE", identifier="@mikro/roi", nullable=False, scope="GLOBAL"), nullable=False, effects=[])],
        port_groups=[models.PortGroupInputModel(key="default", hidden=False)]
    ),
    models.DefinitionInputModel(
        name="Deconvolve Image",
        kind="FUNCTION",
        description="Deconvolve the Image",
        args=[models.PortInputModel(
            key="image", scope="GLOBAL", kind="STRUCTURE", identifier="@mikro/image", effects=[])],
        returns=[models.PortInputModel(key="deconvolved_image", scope="GLOBAL", kind="STRUCTURE", identifier="@mikro/image", nullable=False, effects=[])],
        port_groups=[models.PortGroupInputModel(key="default", hidden=False)]
    ),
    models.DefinitionInputModel(
        name="Roi to Position",
        kind="FUNCTION",
        description="Convert a Roi to a Position on the stage",
        args=[models.PortInputModel(
            key="roi", scope="GLOBAL", kind="STRUCTURE", identifier="@mikro/roi", effects=[])],
        returns=[models.PortInputModel(key="deconvolved_image", scope="GLOBAL", kind="STRUCTURE", identifier="@mikro/position", nullable=False, effects=[])],
        port_groups=[models.PortGroupInputModel(key="default", hidden=False)]
    ),
    models.DefinitionInputModel(
        name="Acquire Position",
        kind="FUNCTION",
        description="Acquire an image at the Positions",
        args=[models.PortInputModel(
            key="image", scope="GLOBAL", kind="STRUCTURE", identifier="@mikro/position", effects=[])],
        returns=[models.PortInputModel(key="acquired_image", scope="GLOBAL", kind="STRUCTURE", identifier="@mikro/image", nullable=False, effects=[])],
        port_groups=[models.PortGroupInputModel(key="default", hidden=False)]
    ),
]





class Command(BaseCommand):
    help = "Creates all of the reactive nodes"

    def handle(self, *args, **kwargs):




        for definition in definitions:

            create_node_from_definition(definition)

