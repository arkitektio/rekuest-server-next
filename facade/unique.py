import hashlib
from rekuest_core.inputs import models 
from rekuest_core import enums, scalars
import json

def calculate_node_hash(definition: models.DefinitionInputModel) -> scalars.NodeHash:
    """Calculates the hash for a node."""
    return hashlib.sha256(
        json.dumps(definition.dict(), sort_keys=True).encode("utf-8")
    ).hexdigest()


def traverse_scope(port: models.ChildPortInputModel, scope=enums.PortScope.LOCAL):
    if port.kind == enums.PortKind.STRUCTURE:
        if port.scope == scope:
            return True
    if port.children:
        return any(traverse_scope(child, scope) for child in port.children)
    return False


def has_locals(ports: list[models.ChildPortInputModel]):
    for port in ports:
        if traverse_scope(port, enums.PortScope.LOCAL):
            return True
    return False


def infer_node_scope(definition: models.DefinitionInputModel):
    has_local_argports = has_locals(definition.args)
    has_local_returnports = has_locals(definition.returns)

    if has_local_argports and has_local_returnports:
        return enums.NodeScope.LOCAL
    if not has_local_argports and not has_local_returnports:
        return enums.NodeScope.GLOBAL
    if not has_local_argports and has_local_returnports:
        return enums.NodeScope.BRIDGE_GLOBAL_TO_LOCAL
    if has_local_argports and not has_local_returnports:
        return enums.NodeScope.BRIDGE_LOCAL_TO_GLOBAL
