from facade.models import Protocol
from rekuest_core.enums import PortKind
from rekuest_core.inputs.models import DefinitionInputModel


def is_hook(definition: DefinitionInputModel) -> Protocol:
    print(definition)

    if not definition.args:
        return None

    if len(definition.args) != 1:
        return None

    if definition.args[0].identifier == "@rekuest/assignationevent":
        x, _ = Protocol.objects.update_or_create(
            name="hook", defaults=dict(description="Is this a hook?")
        )
        return x
