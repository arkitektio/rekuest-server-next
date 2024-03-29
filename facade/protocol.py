from rekuest_core.inputs.models import DefinitionInputModel
from typing import List
from .models import Protocol
from facade.infererence.is_predicate import is_predicate

functions = [
    is_predicate,
]


def infer_protocols(definition: DefinitionInputModel) -> List[Protocol]:
    """Infer the protocols of a definition"""

    protocols = []
    for func in functions:
        protocol = func(definition)
        if protocol:
            protocols.append(protocol)

    return protocols
