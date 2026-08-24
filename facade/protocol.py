from typing import List

from facade.inference.is_hook import is_hook
from facade.inference.is_agent import is_agent
from facade.inference.is_predicate import is_predicate
from rekuest_core.inputs.models import DefinitionInputModel

from .models import Protocol

functions = [
    is_predicate,
    is_hook,
    is_agent,
]


def infer_protocols(definition: DefinitionInputModel, organization) -> List[Protocol]:
    """Infer the protocols of a definition, scoped to the owning organization."""

    protocols = []
    for func in functions:
        protocol = func(definition, organization)
        if protocol:
            protocols.append(protocol)

    return protocols
