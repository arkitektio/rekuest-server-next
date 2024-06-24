import hashlib
import json
import logging

import strawberry
import strawberry_django
from facade import enums, inputs, models, scalars, types
from facade.protocol import infer_protocols
from facade.unique import infer_node_scope
from kante.types import Info

logger = logging.getLogger(__name__)


def create_template(info: Info, input: inputs.CreateTemplateInput) -> types.Template:
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

        provision = models.Provision.objects.get_or_create(
            template=template,
            agent=agent,
            defaults=dict(
                status=enums.ProvisionStatus.INACTIVE,
            ),
        )

        new_deps = []

        if input.dependencies:
            for i in input.dependencies:

                try:
                    depending_node = models.Node.objects.get(hash=i.hash)
                except models.Node.DoesNotExist:
                    depending_node = None

                dep, _ = models.Dependency.objects.update_or_create(
                    template=template,
                    reference=i.reference,
                    defaults=dict(
                        node=depending_node,
                        initial_hash=i.hash,
                        optional=i.optional,
                        binds=i.binds.dict() if i.binds else None,
                    ),
                )
                new_deps.append(dep)

        for dep in template.dependencies.all():
            if dep not in new_deps:
                dep.delete()

        if template.node.hash != hash:
            if template.node.templates.count() == 1:
                logger.info("Deleting Node because it has no more templates")
                template.node.delete()

        template.node = node
        template.extension = input.extension
        template.dynamic = input.dynamic
        template.save()

    except models.Template.DoesNotExist:
        template = models.Template.objects.create(
            interface=input.interface,
            node=node,
            agent=agent,
            extension=input.extension,
            dynamic=input.dynamic
        )

        provision = models.Provision.objects.get_or_create(
            template=template,
            agent=agent,
            defaults=dict(
                status=enums.ProvisionStatus.INACTIVE,
            ),
        )

        new_deps = []

        if input.dependencies:

            for i in input.dependencies:

                try:
                    depending_node = models.Node.objects.get(hash=i.hash)
                except models.Node.DoesNotExist:
                    depending_node = None

                dep, _ = models.Dependency.objects.update_or_create(
                    template=template,
                    reference=i.reference,
                    defaults=dict(
                        node=depending_node,
                        initial_hash=i.hash,
                        optional=i.optional,
                        binds=i.binds.dict() if i.binds else None,
                    ),
                )
                new_deps.append(dep)

    return template
