from facade.models import Protocol
from rekuest_core.inputs.models import DefinitionInputModel


def is_agent(definition: DefinitionInputModel) -> Protocol:
    """ Check if the definition is an LLM agent. """

    if not definition.args:
        return None

    if len(definition.args) != 1:
        return None

    if definition.args[0].identifier == "@lok/room":
        x, _ = Protocol.objects.update_or_create(
            name="agent", defaults=dict(description="Is this a agent?")
        )
        return x
