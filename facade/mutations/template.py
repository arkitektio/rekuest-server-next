from kante.types import Info
import strawberry_django
import strawberry
from facade import types, models, inputs, enums, scalars
import hashlib
import json
import logging
from facade.protocol import infer_protocols
from facade.unique import infer_node_scope

logger = logging.getLogger(__name__)




@strawberry.input
class CreateTemplateInput:
    definition: inputs.DefinitionInput
    dependencies: inputs.DependencyInput | None = None
    interface: str
    params: scalars.AnyDefault | None = None
    instance_id: scalars.InstanceID | None = None


def create_template(info: Info, input: CreateTemplateInput) -> types.Template:
    print(info.context.request.headers)

    registry, _ = models.Registry.objects.update_or_create(
        app=info.context.request.app,
        user=info.context.request.user,
    )

    agent, _ = models.Agent.objects.update_or_create(
        registry=registry,
        instance_id=input.instance_id or "default",
        defaults=dict(
            name=f"{str(registry)} on {input.instance_id}",
        ),
    )

    definition = input.definition

    hash = hashlib.sha256(
        json.dumps(strawberry.asdict(input.definition), sort_keys=True).encode()
    ).hexdigest()
    print(hash)

    try:
        node = models.Node.objects.get(hash=hash)
    except models.Node.DoesNotExist:
        scope = infer_node_scope(input.definition)
        node = models.Node.objects.create(
            hash=hash,
            description=definition.description or "No description",
            args=[strawberry.asdict(i) for i in definition.args],
            scope=scope,
            kind=definition.kind,
            port_groups=[strawberry.asdict(i) for i in definition.port_groups],
            returns=[strawberry.asdict(i) for i in definition.returns],
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

