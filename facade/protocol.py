from typing import List

from facade.infererence.is_hook import is_hook
from facade.infererence.is_predicate import is_predicate
from rekuest_core.inputs.models import DefinitionInputModel

from .models import Protocol

functions = [
    is_predicate,
    is_hook,
]


def infer_protocols(definition: DefinitionInputModel) -> List[Protocol]:
    """Infer the protocols of a definition"""

    protocols = []
    for func in functions:
        protocol = func(definition)
        if protocol:
            protocols.append(protocol)

    return protocols

    return protocols
