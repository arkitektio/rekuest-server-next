from django.core.management.base import BaseCommand
from django.conf import settings
from facade.models import  Agent, Registry
from rekuest_core.inputs import models 
from facade.unique import calculate_node_hash, infer_node_scope
from facade.creation import create_template_from_definition
from authentikate.models import App
from django.contrib.auth import get_user_model
from facade.inputs import CreateTemplateInputModel
from pydantic import BaseModel
from typing import Optional

def create_n_empty_streams(n):
    return [list() for i in range(n)]


class DemoApp(BaseModel):
    name: str
    client_id: Optional[str]
    definitions: dict[str, models.DefinitionInputModel]





app_one = DemoApp(
    name="App One",
    client_id="app_one",
    definitions = {
        "add" : models.DefinitionInputModel(
            name="Add",
            kind="FUNCTION",
            description="Calculate {{a}} + {{b}}",
            args=[models.PortInputModel(
                key="a", scope="GLOBAL", kind="INT", description="The first number", nullable=False, effects=[]), models.PortInputModel(key="b", scope="GLOBAL", description="The sconed number", kind="FLOAT", nullable=False, effects=[])],
            returns=[models.PortInputModel(key="sum", scope="GLOBAL", description="The resulting sum", kind="FLOAT", nullable=False, effects=[])],
            port_groups=[models.PortGroupInputModel(key="default", hidden=False)]
        ),
        "subtract": models.DefinitionInputModel(
            name="Subtract",
            kind="FUNCTION",
            description="Calculate {{a}} - {{b}}",
            args=[models.PortInputModel(
                key="a", scope="GLOBAL", kind="INT", description="The first number", nullable=False, effects=[]), models.PortInputModel(key="b", scope="GLOBAL", description="The subtractor", kind="FLOAT", nullable=False, effects=[], validators=[])],
            returns=[models.PortInputModel(key="difference", scope="GLOBAL", description="The resulting number", kind="FLOAT", nullable=False, effects=[])],
            port_groups=[models.PortGroupInputModel(key="default", hidden=False)]
        ),
        "is_bigger" : models.DefinitionInputModel(
            name="Is Bigger",
            kind="FUNCTION",
            description="Checks if {{a}} is bigger than {{b}}",
            args=[models.PortInputModel(
                key="a", scope="GLOBAL", kind="INT", description="The number to compare", nullable=False, effects=[]),
                models.PortInputModel(
                key="b", scope="GLOBAL", kind="INT", description="The number to compare to ", nullable=True, effects=[], default=3)],
            returns=[models.PortInputModel(key="bigger", scope="GLOBAL", kind="BOOL", description="If a is bigger than b", nullable=False, effects=[])],
            port_groups=[models.PortGroupInputModel(key="default", hidden=False)]
        ),
        "add" : models.DefinitionInputModel(
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
        "double": models.DefinitionInputModel(
            name="Double",
            kind="FUNCTION",
            description="Double {{a}}",
            args=[models.PortInputModel(
                key="a", scope="GLOBAL", kind="INT", nullable=False, effects=[])],
            returns=[models.PortInputModel(key="bigger", scope="GLOBAL", kind="INT", nullable=False, effects=[])],
            port_groups=[models.PortGroupInputModel(key="default", hidden=False)]
        )},
)

mikro_app = DemoApp(
    name="Mikro",
    user="johannes",
    definitions= {
        "acquire_image" : models.DefinitionInputModel(
            name="Acquire Image",
            kind="FUNCTION",
            description="Acquires an Z-stack of size {{z}} at the current position",
            args=[models.PortInputModel(
                key="z", scope="GLOBAL", kind="INT", description="The size of z slices", nullable=True, effects=[], default=70)],
            returns=[models.PortInputModel(key="image", scope="GLOBAL", kind="STRUCTURE", identifier="@mikro/image", description="The acquired image", nullable=False, effects=[])],
            port_groups=[models.PortGroupInputModel(key="default", hidden=False)]
        ),
        "segment_cells" : models.DefinitionInputModel(
            name="Segment Cells",
            kind="FUNCTION",
            description="Segment the Cells in the image",
            args=[models.PortInputModel(
                key="z", scope="GLOBAL", kind="STRUCTURE", identifier="@mikro/image", nullable=False, effects=[]),
                models.PortInputModel(
                    key="label_to_assign", scope="GLOBAL", kind="STRING", description="Which label should we assign?", nullable=True, effects=[], default="cell"),
                ],
            returns=[models.PortInputModel(key="segmented_image", scope="GLOBAL", kind="STRUCTURE", identifier="@mikro/image", description="The segmented image", nullable=False, effects=[])],
            port_groups=[models.PortGroupInputModel(key="default", hidden=False)]
        ),
        "mark_clusters" : models.DefinitionInputModel(
            name="Mark Clusters",
            kind="FUNCTION",
            description="Mark Clusters in the Image",
            args=[models.PortInputModel(
                key="z", scope="GLOBAL", kind="STRUCTURE", identifier="@mikro/image")],
            returns=[models.PortInputModel(key="clusters", scope="GLOBAL", kind="LIST", child=models.ChildPortInputModel(kind="STRUCTURE", identifier="@mikro/roi", nullable=False, scope="GLOBAL"), nullable=False, effects=[])],
            port_groups=[models.PortGroupInputModel(key="default", hidden=False)]
        ),
        "deconvolve_image" : models.DefinitionInputModel(
            name="Deconvolve Image",
            kind="FUNCTION",
            description="Deconvolve the Image",
            args=[models.PortInputModel(
                key="image", scope="GLOBAL", kind="STRUCTURE", identifier="@mikro/image", effects=[])],
            returns=[models.PortInputModel(key="deconvolved_image", scope="GLOBAL", kind="STRUCTURE", identifier="@mikro/image", nullable=False, effects=[])],
            port_groups=[models.PortGroupInputModel(key="default", hidden=False)]
        ),
        "roi_to_position" : models.DefinitionInputModel(
            name="Roi to Position",
            kind="FUNCTION",
            description="Convert a Roi to a Position on the stage",
            args=[models.PortInputModel(
                key="roi", scope="GLOBAL", kind="STRUCTURE", identifier="@mikro/roi", effects=[])],
            returns=[models.PortInputModel(key="deconvolved_image", scope="GLOBAL", kind="STRUCTURE", identifier="@mikro/position", nullable=False, effects=[])],
            port_groups=[models.PortGroupInputModel(key="default", hidden=False)]
        ),
        "acquire_position": models.DefinitionInputModel(
            name="Acquire Position",
            kind="FUNCTION",
            description="Acquire an image at the Positions",
            args=[models.PortInputModel(
                key="image", scope="GLOBAL", kind="STRUCTURE", identifier="@mikro/position", effects=[])],
            returns=[models.PortInputModel(key="acquired_image", scope="GLOBAL", kind="STRUCTURE", identifier="@mikro/image", nullable=False, effects=[])],
            port_groups=[models.PortGroupInputModel(key="default", hidden=False)]
        ),
        
      
    }
    
)


numpy_app = DemoApp(
    name = "Numpy",
    definitions= {
        "to_numpy" : models.DefinitionInputModel(
            name="To Numpy",
            kind="FUNCTION",
            description="Converts an Image to a 5D Numpy Array",
            args=[models.PortInputModel(
                key="image", scope="GLOBAL", kind="STRUCTURE", identifier="@mikro/image", effects=[])],
            returns=[models.PortInputModel(key="acquired_image", scope="LOCAL", kind="STRUCTURE", identifier="@numpy/np.array:5D", nullable=False, effects=[])],
            port_groups=[models.PortGroupInputModel(key="default", hidden=False)]
        ),
        "max_project": models.DefinitionInputModel(
            name="Max Project",
            kind="FUNCTION",
            description="Projects 5D Numpy Array to  a 4D Numpy Array along a dimension",
            args=[models.PortInputModel(
                key="image", scope="LOCAL", kind="STRUCTURE", identifier="@numpy/np.array:5D", effects=[]),
                models.PortInputModel(
                key="dim", scope="GLOBAL", kind="INT", nullable=True, effects=[], default=0)
            ],
            returns=[models.PortInputModel(key="acquired_image", scope="LOCAL", kind="STRUCTURE", identifier="@numpy/np.array:4D", nullable=False, effects=[])],
            port_groups=[models.PortGroupInputModel(key="default", hidden=False)]
        ),
        "reshape_to_5d" : models.DefinitionInputModel(
            name="Reshape to 5D",
            kind="FUNCTION",
            description="Reshaes a 4D Numpy Array to a 5D Numpy Array",
            args=[models.PortInputModel(
                key="image", scope="LOCAL", kind="STRUCTURE", identifier="@numpy/np.array:4D", effects=[]),
                models.PortInputModel(
                key="dim", scope="GLOBAL", kind="INT", nullable=True, effects=[], default=0)
            ],
            returns=[models.PortInputModel(key="acquired_image", scope="LOCAL", kind="STRUCTURE", identifier="@numpy/np.array:5D", nullable=False, effects=[])],
            port_groups=[models.PortGroupInputModel(key="default", hidden=False)]
        ),
         "to_image" : models.DefinitionInputModel(
            name="To Image",
            kind="FUNCTION",
            description="Converts an 5D Numpy Array to an Image",
            args=[models.PortInputModel(
                key="image", scope="LOCAL", kind="STRUCTURE", identifier="@numpy/np.array:5D", effects=[])],
            returns=[models.PortInputModel(key="acquired_image", scope="GLOBAL", kind="STRUCTURE", identifier="@mikro/image", nullable=False, effects=[])],
            port_groups=[models.PortGroupInputModel(key="default", hidden=False)]
        ),
    }

)


image_j_app = DemoApp(
    name="ImageJ",
    definitions= {
        "to_imagej" : models.DefinitionInputModel(
            name="To ImageJPlus",
            kind="FUNCTION",
            description="Converts an Image to an ImageJ Plus",
            args=[models.PortInputModel(
                key="image", scope="GLOBAL", kind="STRUCTURE", identifier="@mikro/image", effects=[])],
            returns=[models.PortInputModel(key="acquired_image", scope="LOCAL", kind="STRUCTURE", identifier="@imagej/plus", nullable=False, effects=[])],
            port_groups=[models.PortGroupInputModel(key="default", hidden=False)]
        ),
        "max_project": models.DefinitionInputModel(
            name="Max Project",
            kind="FUNCTION",
            description="Projects an ImageJ Plus",
            args=[models.PortInputModel(
                key="image", scope="LOCAL", kind="STRUCTURE", identifier="@imagej/plus", effects=[]),
                models.PortInputModel(
                key="dim", scope="GLOBAL", kind="INT", nullable=True, effects=[], default=0)
            ],
            returns=[models.PortInputModel(key="acquired_image", scope="GLOBAL", kind="STRUCTURE", identifier="@imagej/plus", nullable=False, effects=[])],
            port_groups=[models.PortGroupInputModel(key="default", hidden=False)]
        ),
        "deconvolve" : models.DefinitionInputModel(
            name="Deconvolve",
            kind="FUNCTION",
            description="Deconvolve an ImageJplus Image to ImageJPlus",
            args=[models.PortInputModel(
                key="image", scope="LOCAL", kind="STRUCTURE", identifier="@imagej/plus", effects=[]),
                models.PortInputModel(
                key="dim", scope="GLOBAL", kind="INT", nullable=True, effects=[], default=0)
            ],
            returns=[models.PortInputModel(key="acquired_image", scope="GLOBAL", kind="STRUCTURE", identifier="@imagej/plus", nullable=False, effects=[])],
            port_groups=[models.PortGroupInputModel(key="default", hidden=False)]
        ),
        "to_image" : models.DefinitionInputModel(
            name="To Image",
            kind="FUNCTION",
            description="Converts an ImageJ Plus to an Image",
            args=[models.PortInputModel(
                key="image", scope="LOCAL", kind="STRUCTURE", identifier="@imagej/plus", effects=[])],
            returns=[models.PortInputModel(key="acquired_image", scope="GLOBAL", kind="STRUCTURE", identifier="@mikro/image", nullable=False, effects=[])],
            port_groups=[models.PortGroupInputModel(key="default", hidden=False)]
        ),
    }
)


decided_app = DemoApp(
    name="Smart App",
    definitions= {
        "labels_exceed" : models.DefinitionInputModel(
            name="Labels Exceed Amount",
            kind="FUNCTION",
            description="Checks if there are more than {{threshold}} labels of type {{label_to_test}} in the image",
            args=[models.PortInputModel(
                key="image", scope="GLOBAL", kind="STRUCTURE", identifier="@mikro/image", effects=[], description="The labeled image to inspect",),
                models.PortInputModel(
                key="threshold", scope="GLOBAL", kind="INT", nullable=True, effects=[], default=70, description="The threshold of labels that the image needs"),
                models.PortInputModel(
                key="label_to_test", scope="GLOBAL", kind="STRING", nullable=True, effects=[],  description="The label to test", default="cell"),
        ],
            returns=[models.PortInputModel(key="is_bigger", description="If the amount is exceeded", scope="GLOBAL", kind="BOOL", nullable=False, effects=[])],
            port_groups=[models.PortGroupInputModel(key="default", hidden=False)]
        ),
        
    }
)

reorder_needed_app = DemoApp(
    name ="Reorder Needed App",
    definitions= {
        "other_stuff" : models.DefinitionInputModel(
            name="Passes out weird",
            kind="FUNCTION",
            description="Checks if there are more than {{threshold}} labels of type {{label_to_test}} in the image",
            args=[models.PortInputModel(
                key="image", scope="GLOBAL", kind="STRUCTURE", identifier="@mikro/image", effects=[], description="The labeled image to inspect",),
                models.PortInputModel(
                key="house", scope="GLOBAL", kind="INT", effects=[],description="The threshold of labels that the image needs")
        ],
            returns=[models.PortInputModel(
                key="image", scope="GLOBAL", kind="STRUCTURE", identifier="@mikro/image", effects=[], description="The labeled image to inspect",),
                models.PortInputModel(
                key="house", scope="GLOBAL", kind="INT", effects=[],description="The threshold of labels that the image needs")],
            port_groups=[models.PortGroupInputModel(key="default", hidden=False)]
        ),
        "labels_exceed" : models.DefinitionInputModel(
            name="Needs Reorder",
            kind="FUNCTION",
            description="Checks if there are more than {{threshold}} labels of type {{label_to_test}} in the image",
            args=[
                models.PortInputModel(
                key="house", scope="GLOBAL", kind="INT", effects=[],description="The threshold of labels that the image needs"),
                models.PortInputModel(
                key="image", scope="GLOBAL", kind="STRUCTURE", identifier="@mikro/image", effects=[], description="The labeled image to inspect",),
                
        ],
            returns=[models.PortInputModel(key="is_bigger", description="If the amount is exceeded", scope="GLOBAL", kind="BOOL", nullable=False, effects=[])],
            port_groups=[models.PortGroupInputModel(key="default", hidden=False)]
        ),
        
    }
)





apps = [app_one, mikro_app, numpy_app, image_j_app,decided_app, reorder_needed_app]


class Command(BaseCommand):
    help = "Creates all of the reactive nodes"

    def handle(self, *args, **kwargs):


        for app in apps:
            
            fake_user = get_user_model().objects.first()

            fake_app, _ = App.objects.get_or_create(name=app.name, client_id=app.name)


            registry, _ = Registry.objects.update_or_create(
                app=fake_app,
                user=fake_user,
            )

            agent, _ = Agent.objects.update_or_create(
                registry=registry,
                instance_id="default",
                defaults=dict(
                    name=f"{str(registry)} on default",
                ),
            )

            for interface, definition in app.definitions.items():

                
                input = CreateTemplateInputModel(
                    interface=interface,
                    definition=definition
                )



                create_template_from_definition(input, agent)

