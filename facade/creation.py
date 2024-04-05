import hashlib
import json
from rekuest_core.inputs import types as ritypes
from facade import models, inputs
from facade.protocol import infer_protocols
from facade.unique import infer_node_scope

import logging

logger = logging.getLogger(__name__)



def create_template_from_definition(input: inputs.CreateTemplateInput, agent: models.Agent) -> models.Template:

    node = create_node_from_definition(input.definition)

    try:
        template = models.Template.objects.get(
            interface=input.interface,
            agent=agent,
        )

        if template.node.hash != hash:
            if template.node.templates.count() == 1:
                logger.info("Deleting Node because it has no more templates")
                template.node.delete()

        template.node = node
        template.save()

    except models.Template.DoesNotExist:
        template = models.Template.objects.create(
            interface=input.interface,
            node=node,
            agent=agent,
        )

    return template




def create_node_from_definition(definition: ritypes.DefinitionInput) -> models.Node:


    hash = hashlib.sha256(
        json.dumps(definition.dict(), sort_keys=True).encode()
    ).hexdigest()
     
    print(hash)

    try:
        node = models.Node.objects.get(hash=hash)
    except models.Node.DoesNotExist:
        scope = infer_node_scope(definition)
        node = models.Node.objects.create(
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
        node.protocols.add(*protocols)

        if definition.is_test_for:
            for nodehash in definition.is_test_for:
                node.is_test_for.add(models.Node.objects.get(hash=nodehash))

        if definition.collections:
            for collection_name in definition.collections:
                c, _ = models.Collection.objects.get_or_create(name=collection_name)
                node.collections.add(c)

        logger.info(f"Created {node}")

    return node