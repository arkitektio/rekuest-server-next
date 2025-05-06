import hashlib
import json
import logging

import strawberry
from facade import inputs, models, types
from facade.protocol import infer_protocols
from facade.unique import assert_non_statefullness, infer_action_scope
from kante.types import Info
from rekuest_core.inputs.models import DefinitionInputModel, ImplementationInputModel
from authentikate.vars import get_user, get_client
logger = logging.getLogger(__name__)


def hash_definition(definition: DefinitionInputModel) -> str:
    hashable_definition = {
        key: value
        for key, value in dict(strawberry.asdict(definition)).items()
        if key
        in [
            "name",
            "description",
            "args",
            "returns",
            "stateful",
            "is_test_for",
            "collections",
        ]
    }
    return hashlib.sha256(
        json.dumps(hashable_definition, sort_keys=True).encode()
    ).hexdigest()


def _create_implementation(
    input: ImplementationInputModel, agent: models.Agent, extension: str
) -> models.Implementation:
    definition = input.definition

    hash = hash_definition(definition)

    try:
        action = models.Action.objects.get(hash=hash)
    except models.Action.DoesNotExist:
        scope = infer_action_scope(definition)

        if definition.stateful is False:
            assert_non_statefullness(definition)

        action = models.Action.objects.create(
            hash=hash,
            description=definition.description or "No description",
            args=[strawberry.asdict(i) for i in definition.args],
            scope=scope,
            stateful=definition.stateful,
            kind=definition.kind,
            port_groups=[strawberry.asdict(i) for i in definition.port_groups],
            returns=[strawberry.asdict(i) for i in definition.returns],
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
        action.save()

    try:
        implementation = models.Implementation.objects.get(
            interface=input.interface,
            agent=agent,
        )

        new_deps = []

        if input.dependencies:
            for i in input.dependencies:
                try:
                    depending_action = models.Action.objects.get(hash=i.hash)
                except models.Action.DoesNotExist:
                    depending_action = None

                dep, _ = models.Dependency.objects.update_or_create(
                    implementation=implementation,
                    reference=i.reference,
                    defaults=dict(
                        action=depending_action,
                        initial_hash=i.hash,
                        optional=i.optional,
                        binds=i.binds.dict() if i.binds else None,
                    ),
                )
                new_deps.append(dep)

        for dep in implementation.dependencies.all():
            if dep not in new_deps:
                dep.delete()

        if implementation.action.hash != hash:
            if implementation.action.implementations.count() == 1:
                logger.info("Deleting Action because it has no more implementations")
                implementation.action.delete()

        implementation.action = action
        implementation.extension = extension
        implementation.dynamic = input.dynamic
        implementation.params = input.params or {}
        implementation.save()

    except models.Implementation.DoesNotExist:
        implementation = models.Implementation.objects.create(
            interface=input.interface,
            action=action,
            agent=agent,
            extension=extension,
            dynamic=input.dynamic,
            params=input.params or {},
        )

        new_deps = []

        if input.dependencies:
            for i in input.dependencies:
                try:
                    depending_action = models.Action.objects.get(hash=i.hash)
                except models.Action.DoesNotExist:
                    depending_action = None

                dep, _ = models.Dependency.objects.update_or_create(
                    implementation=implementation,
                    reference=i.reference,
                    defaults=dict(
                        action=depending_action,
                        initial_hash=i.hash,
                        optional=i.optional,
                        binds=i.binds.dict() if i.binds else None,
                    ),
                )
                new_deps.append(dep)

    return implementation


def create_implementation(
    info: Info, input: inputs.CreateImplementationInput
) -> types.Implementation:
    user = get_user()
    client = get_client()
    
    
    registry, _ = models.Registry.objects.update_or_create(
        client=client,
        user=user,
    )

    agent, _ = models.Agent.objects.update_or_create(
        registry=registry,
        instance_id=input.instance_id or "default",
        defaults=dict(
            name=f"{str(registry)} on {input.instance_id}",
        ),
    )

    return _create_implementation(input.implementation, agent, input.extension)


def create_foreign_implementation(
    info: Info, input: inputs.CreateForeignImplementationInput
) -> types.Implementation:
    agent = models.Agent.objects.get(id=input.agent)

    assert input.extension in agent.extensions, (
        f"Extension {input.extension} not supported by agent {agent}"
    )

    return _create_implementation(input.implementation, agent, input.extension)


def delete_implementation(info: Info, input: inputs.DeleteImplementationInput) -> str:
    implementation = models.Implementation.objects.get(id=input.implementation)

    implementation.delete()

    return input.id


def set_extension_implementations(
    info: Info, input: inputs.SetExtensionImplementationsInput
) -> list[types.Implementation]:
    
    user = get_user()
    client = get_client()
    
    
    registry, _ = models.Registry.objects.update_or_create(
        client=client,
        user=user,
    )

    agent, _ = models.Agent.objects.get_or_create(
        registry=registry,
        instance_id=input.instance_id or "default",
        defaults=dict(
            name=f"{str(registry)} on {input.instance_id}",
        ),
    )

    previous_implementations = models.Implementation.objects.filter(
        agent=agent, extension=input.extension
    ).all()

    created_implementations_id = []
    created_implementations = []
    for implementation in input.implementations:
        created_implementation = _create_implementation(
            implementation, agent, input.extension
        )

        created_implementations_id.append(created_implementation.id)
        created_implementations.append(created_implementation)

    if input.run_cleanup:
        for i in previous_implementations:
            if i.id not in created_implementations_id:
                i.delete()

    return created_implementations


def pin_implementation(info, input: inputs.PinInput) -> types.Implementation:
    
    user = get_user()
    
    
    agent = models.Implementation.objects.get(id=input.id)
    if input.pin:
        agent.pinned_by.add(user)
    else:
        agent.pinned_by.remove(user)
    agent.save()
    return agent
