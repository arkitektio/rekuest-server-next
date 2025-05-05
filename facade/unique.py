import hashlib
from rekuest_core.inputs import models
from rekuest_core import enums, scalars
import json


def calculate_action_hash(
    definition: models.DefinitionInputModel,
) -> scalars.ActionHash:
    """Calculates the hash for a action."""
    return hashlib.sha256(
        json.dumps(definition.dict(), sort_keys=True).encode("utf-8")
    ).hexdigest()


def traverse_scope(port: models.PortInputModel):
    if port.kind == enums.PortKind.MEMORY_STRUCTURE:
        return True
    if port.children:
        return any(traverse_scope(child) for child in port.children)
    return False


def has_locals(ports: list[models.PortInputModel]):
    for port in ports:
        if traverse_scope(port):
            return True
    return False


def traverse_state_dependency(port: models.PortInputModel):
    if port.assign_widget:
        pass
    if port.children:
        return any(traverse_state_dependency(child) for child in port.children)


def infer_action_scope(definition: models.DefinitionInputModel):
    has_local_argports = has_locals(definition.args)
    has_local_returnports = has_locals(definition.returns)

    if has_local_argports and has_local_returnports:
        return enums.ActionScope.LOCAL
    if not has_local_argports and not has_local_returnports:
        return enums.ActionScope.GLOBAL
    if not has_local_argports and has_local_returnports:
        return enums.ActionScope.BRIDGE_GLOBAL_TO_LOCAL
    if has_local_argports and not has_local_returnports:
        return enums.ActionScope.BRIDGE_LOCAL_TO_GLOBAL


def assert_non_statefullness(definition: models.DefinitionInputModel):
    """Asserts that the definition is correctly stateful."""
    for port in definition.args:
        traverse_state_dependency(port)
