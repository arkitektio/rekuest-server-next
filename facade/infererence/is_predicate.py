from facade.inputs import DefinitionInput
from facade.models import Protocol
from facade.enums import PortKind

def is_predicate(definition: DefinitionInput) -> Protocol:
    print(definition)

    if not definition.returns:
        return None


    if len(definition.returns) != 1:
        return None

    if definition.returns[0].kind == PortKind.BOOL:
        x, _ = Protocol.objects.update_or_create(
            name="predicate", defaults=dict(description="Is this a predicate?")
        )
        return x