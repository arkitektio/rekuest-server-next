from kante.types import Info
import strawberry_django
import strawberry
from facade import types, models, inputs, enums, scalars
import hashlib
import json
import logging
from facade.protocol import infer_protocols
from facade.utils import hash_input
import uuid

logger = logging.getLogger(__name__)


def create_shortcut(info: Info, input: inputs.CreateShortcutInput) -> types.Shortcut:
    
    
    toolbox = models.Toolbox.objects.get(id=input.toolbox) if input.toolbox else models.Toolbox.objects.get_or_create(
        name="default",
        defaults=dict(
            description="Default toolbox",
            creator=info.context.request.user,
        )
    )[0]
    
    
    node = models.Node.objects.get(id=input
    .node)
    
    args = [arg for arg in node.args if arg["key"] not in input.args]
    returns = [arg for arg in node.returns if arg["key"] not in []]
    
    

    shortcut = models.Shortcut.objects.create(
        name=input.name,
        description=input.description,
        node_id=input.node,
        creator=info.context.request.user,
        saved_args=input.args,
        toolbox=toolbox,
        args=args,
        returns=returns,
        allow_quick=input.allow_quick,
        use_returns=input.use_returns
    )


    logger.info(f"Shortcut created: {shortcut}")

    return shortcut
