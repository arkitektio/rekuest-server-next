import hashlib
import json
import logging

import strawberry
import strawberry_django
from facade import enums, inputs, models, scalars, types
from facade.protocol import infer_protocols
from facade.unique import infer_node_scope
from kante.types import Info
from rekuest_core.inputs.models import DefinitionInputModel, TemplateInputModel

logger = logging.getLogger(__name__)

def hash_definition(definition: DefinitionInputModel) -> str:
    hashable_definition = {
        key: value
        for key, value in dict(strawberry.asdict(definition)).items()
        if key in ["name", "description", "args", "returns"]
    }
    return hashlib.sha256(
        json.dumps(hashable_definition, sort_keys=True).encode()
    ).hexdigest()



def _create_template(input: TemplateInputModel, agent: models.Agent, extension: str) -> models.Template:

    definition= input.definition

    hash = hash_definition(definition)

    try:
        node = models.Node.objects.get(hash=hash)
    except models.Node.DoesNotExist:
        scope = infer_node_scope(definition)
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

                print(i)

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
        template.extension = extension
        template.dynamic = input.dynamic
        template.params = input.params or {}
        template.save()

    except models.Template.DoesNotExist:
        template = models.Template.objects.create(
            interface=input.interface,
            node=node,
            agent=agent,
            extension=extension,
            dynamic=input.dynamic,
            params=input.params or {},
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

    return _create_template(input.template, agent, input.extension)



def create_foreign_template(info: Info, input: inputs.CreateForeignTemplateInput) -> types.Template:
    

    agent = models.Agent.objects.get(
        id=input.agent
    )

    assert input.extension in agent.extensions, f"Extension {input.extension} not supported by agent {agent}"

    return _create_template(input.template, agent, input.extension)

    
def delete_template(info: Info, input: inputs.DeleteTemplateInput) -> str:
    

    template = models.Template.objects.get(
        id=input.template
    )

    template.delete()


    return input.id




def set_extension_templates(info: Info, input: inputs.SetExtensionTemplatesInput) -> list[types.Template]:

    registry, _ = models.Registry.objects.update_or_create(
        app=info.context.request.app,
        user=info.context.request.user,
    )

    agent, _ = models.Agent.objects.get_or_create(
        registry=registry,
        instance_id=input.instance_id or "default",
        defaults=dict(
            name=f"{str(registry)} on {input.instance_id}",
        ),
    )

    

    previous_templates = models.Template.objects.filter(agent=agent, extension=input.extension).all()


    created_templates_id = []
    created_templates = []
    for template in input.templates:

        created_template = _create_template(template, agent, input.extension)

        created_templates_id.append(created_template.id)
        created_templates.append(created_template)


    if input.run_cleanup:
        for i in previous_templates:
            if i.id not in created_templates_id:
                i.delete()
                print("Deleted Template", id)


    return created_templates


