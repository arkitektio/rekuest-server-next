import hashlib
import json
from rekuest_core.inputs import types as ritypes
from facade import models, inputs
from facade.protocol import infer_protocols
from facade.unique import infer_action_scope

import logging

logger = logging.getLogger(__name__)


def create_implementation_from_definition(
    input: inputs.CreateImplementationInput, agent: models.Agent
) -> models.Implementation:
    action = create_action_from_definition(input.definition)

    try:
        implementation = models.Implementation.objects.get(
            interface=input.interface,
            agent=agent,
        )

        if implementation.action.hash != hash:
            if implementation.action.implementations.count() == 1:
                logger.info("Deleting Action because it has no more implementations")
                implementation.action.delete()

        implementation.action = action
        implementation.save()

    except models.Implementation.DoesNotExist:
        implementation = models.Implementation.objects.create(
            interface=input.interface,
            action=action,
            agent=agent,
        )

    return implementation


def create_action_from_definition(definition: ritypes.DefinitionInput) -> models.Action:
    hash = hashlib.sha256(
        json.dumps(definition.dict(), sort_keys=True).encode()
    ).hexdigest()

    try:
        action = models.Action.objects.get(hash=hash)
    except models.Action.DoesNotExist:
        scope = infer_action_scope(definition)
        action = models.Action.objects.create(
            hash=hash,
            description=definition.description or "No description",
            args=[i.dict() for i in definition.args],
            scope=scope,
            kind=definition.kind,
            port_groups=[i.dict() for i in definition.port_groups],
            returns=[i.dict() for i in definition.returns],
            name=definition.name,
        )

        protocols = infer_protocols(definition)
        action.protocols.add(*protocols)

        if definition.is_test_for:
            for actionhash in definition.is_test_for:
                action.is_test_for.add(models.Action.objects.get(hash=actionhash))

        if definition.collections:
            for collection_name in definition.collections:
                c, _ = models.Collection.objects.get_or_create(name=collection_name)
                action.collections.add(c)

        logger.info(f"Created {action}")

    return action
