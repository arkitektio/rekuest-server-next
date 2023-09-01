from kante.types import Info
import strawberry_django
import strawberry
from reaktion import types, models, inputs, enums, scalars
import hashlib
import json
import logging
from facade.protocol import infer_protocols
from facade.utils import hash_input
from reaktion.hashers import hash_graph
import namegenerator

logger = logging.getLogger(__name__)


@strawberry.input
class UpdateWorkspaceInput:
    workspace: strawberry.ID
    graph: inputs.GraphInput
    title: str | None = None
    description: str | None = None


def update_workspace(info: Info, input: UpdateWorkspaceInput) -> types.Workspace:
    return models.Workspace.objects.get(id=input.workspace)


@strawberry.input
class CreateWorkspaceInput:
    graph: inputs.GraphInput | None = None
    title: str | None = None
    description: str | None = None
    vanilla: bool = False


def create_workspace(info: Info, input: CreateWorkspaceInput) -> types.Workspace:
    title = input.title or namegenerator.gen()
    workspace = models.Workspace.objects.create(
        title=title,
        description=input.description,
        creator=info.context.request.user,
    )

    nodes = [
        {
            "id": "1",
            "kind": "ARGS",
            "ins": [[]],
            "outs": [[]],
            "cons": [],
            "position": {"x": 0, "y": 50},
            "constants": [],
            "constants_map": {},
            "globals_map": {},
            "title": "Input",
            "description": "The input to the workflow",
        },
        {
            "id": "2",
            "kind": "RETURNS",
            "ins": [[]],
            "outs": [[]],
            "cons": [],
            "position": {"x": 1500, "y": 50},
            "constants": [],
            "constants_map": {},
            "globals_map": {},
            "title": "Output",
            "description": "The output to the workflow",
        },
    ]

    graph = {
        "nodes": nodes,
        "edges": [],
        "globals": [],
    }

    flow = models.Flow.objects.create(
        workspace=workspace,
        graph=graph,
        hash=hash_graph(graph),
        title=title,
        description=input.description,
        creator=info.context.request.user,
    )

    return workspace
