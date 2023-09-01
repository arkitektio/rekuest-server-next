from kante.types import Info
import strawberry_django
import strawberry
from facade import types, models, inputs, enums, scalars
import hashlib
import json
import logging
from facade.protocol import infer_protocols


logger = logging.getLogger(__name__)


def traverse_scope(port: inputs.ChildPortInput, scope=enums.PortScope.LOCAL):
    if port.kind == enums.PortKind.STRUCTURE:
        if port.scope == scope:
            return True
    if port.child:
        return traverse_scope(port.child, scope)
    return False


def has_locals(ports: list[inputs.ChildPortInput]):
    for port in ports:
        if traverse_scope(port, enums.PortScope.LOCAL):
            return True
    return False


def infer_node_scope(definition: inputs.DefinitionInput):
    has_local_argports = has_locals(definition.args)
    has_local_returnports = has_locals(definition.returns)

    if has_local_argports and has_local_returnports:
        return enums.NodeScope.LOCAL
    if not has_local_argports and not has_local_returnports:
        return enums.NodeScope.GLOBAL
    if not has_local_argports and has_local_returnports:
        return enums.NodeScope.BRIDGE_GLOBAL_TO_LOCAL
    if has_local_argports and not has_local_returnports:
        return enums.NodeScope.BRIDGE_LOCAL_TO_GLOBAL


@strawberry.input
class CreateTemplateInput:
    definition: inputs.DefinitionInput
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
        print(protocols)
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
        template = models.Template.objects.get(interface=input.interface, agent=agent)

        if template.node.hash == hash:
            return template
        else:
            if template.node.templates.count() == 1:
                logger.info("Deleting Node because it has no more templates")
                template.node.delete()

        template.node = node
        template.save()

    except:
        template = models.Template.objects.create(
            interface=input.interface,
            node=node,
            agent=agent,
        )

    return template

    raise NotImplementedError("Mutation create_template is not implemented")
