from typing import List

from facade.infererence.is_hook import is_hook
from facade.infererence.is_agent import is_agent
from facade.infererence.is_predicate import is_predicate
from rekuest_core.inputs.models import DefinitionInputModel

from .models import Protocol

functions = [
    is_predicate,
    is_hook,
    is_agent,
]


def infer_protocols(definition: DefinitionInputModel) -> List[Protocol]:
    """Infer the protocols of a definition"""

    protocols = []
    for func in functions:
        protocol = func(definition)
        if protocol:
            protocols.append(protocol)

    return protocols
