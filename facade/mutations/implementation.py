import hashlib
import json
import logging

import strawberry
from facade import inputs, models, types
from facade.protocol import infer_protocols
from facade.unique import assert_non_statefullness, infer_action_scope
from kante.types import Info
from rekuest_core.inputs.models import DefinitionInputModel, ImplementationInputModel, PortInputModel
from rekuest_core.enums import PortKind
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
    return hashlib.sha256(json.dumps(hashable_definition, sort_keys=True).encode()).hexdigest()


def extract_structure_recursively(structures: list[str], definition: PortInputModel):
    if definition.identifier and definition.kind == PortKind.STRUCTURE:
        structures.append(definition.identifier)

    for port in definition.children or []:
        extract_structure_recursively(structures, port)


def extract_structures(definition: DefinitionInputModel) -> list[str]:
    structures = []
    for port in definition.args + definition.returns:
        extract_structure_recursively(structures, port)

    return list(set(structures))


def extract_interfaces_recursively(interfaces: list[str], definition: PortInputModel):
    if definition.identifier and definition.kind == PortKind.INTERFACE:
        interfaces.append(definition.identifier)

    for port in definition.children or []:
        extract_interfaces_recursively(interfaces, port)


def extract_interfaces(definition: DefinitionInputModel) -> list[str]:
    interfaces = []
    for port in definition.args + definition.returns:
        extract_interfaces_recursively(interfaces, port)

    return list(set(interfaces))


def identifier_to_key(identifier: str) -> str:
    if "/" in identifier:
        return identifier.split("/")[-1].strip()

    else:
        raise ValueError(f"Identifier {identifier} does not contain a key part")


def identifier_to_package_key(identifier: str) -> str:
    if "/" in identifier:
        parts = identifier.split("/")[0]
        parts = parts.replace("@", "")

        return parts

    else:
        raise ValueError(f"Identifier {identifier} does not contain a package part")


def recursive_create_input_usages(action: models.Action, port: PortInputModel, index: int, key: str, modifiers: list[str]) -> None:
    if port.kind == PortKind.STRUCTURE and port.identifier:
        structure = models.Structure.objects.get(key=identifier_to_key(port.identifier).lower(), package__key=identifier_to_package_key(port.identifier).lower())

        x = models.InputStructureUsage.objects.update_or_create(
            structure=structure,
            action=action,
            port_index=index,
            port_key=key,
            defaults=dict(
                modifiers=list(modifiers or []),
            ),
        )

    if port.kind == PortKind.INTERFACE and port.identifier:
        interface = models.Interface.objects.get(key=identifier_to_key(port.identifier).lower(), package__key=identifier_to_package_key(port.identifier).lower())

        x = models.InputInterfaceUsage.objects.update_or_create(
            interface=interface,
            action=action,
            port_index=index,
            port_key=key,
            defaults=dict(
                modifiers=list(modifiers or []),
            ),
        )

    if port.kind == PortKind.DICT:
        for i, child in enumerate(port.children or []):
            recursive_create_input_usages(action, child, index, key, modifiers + ["dict"])

    if port.kind == PortKind.LIST:
        for i, child in enumerate(port.children or []):
            recursive_create_input_usages(action, child, index, key, modifiers + ["list"])


def recursive_create_output_usages(action: models.Action, port: PortInputModel, index: int, key: str, modifiers: list[str]) -> None:
    if port.kind == PortKind.STRUCTURE and port.identifier:
        structure = models.Structure.objects.get(key=identifier_to_key(port.identifier).lower(), package__key=identifier_to_package_key(port.identifier).lower())

        x = models.OutputStructureUsage.objects.update_or_create(
            structure=structure,
            action=action,
            port_index=index,
            port_key=key,
            defaults=dict(
                modifiers=modifiers,
            ),
        )

    if port.kind == PortKind.INTERFACE and port.identifier:
        interface = models.Interface.objects.get(key=identifier_to_key(port.identifier).lower(), package__key=identifier_to_package_key(port.identifier).lower())

        x = models.OutputInterfaceUsage.objects.update_or_create(
            interface=interface,
            action=action,
            port_index=index,
            port_key=key,
            defaults=dict(
                modifiers=modifiers,
            ),
        )

    if port.kind == PortKind.DICT:
        for i, child in enumerate(port.children or []):
            recursive_create_input_usages(action, child, index, key, modifiers + ["dict"])

    if port.kind == PortKind.LIST:
        for i, child in enumerate(port.children or []):
            recursive_create_input_usages(action, child, index, key, modifiers + ["list"])


def create_usages(action: models.Action, definition: DefinitionInputModel) -> None:
    for i, port in enumerate(definition.args):
        recursive_create_input_usages(action, port, i, port.key, [])

    for i, port in enumerate(definition.returns):
        recursive_create_output_usages(action, port, i, port.key, [])


def _create_implementation(input: ImplementationInputModel, agent: models.Agent, extension: str) -> models.Implementation:
    definition = input.definition

    hash = hash_definition(definition)

    try:
        action = models.Action.objects.get(hash=hash, organization=agent.registry.organization)
    except models.Action.DoesNotExist:
        scope = infer_action_scope(definition)

        if definition.stateful is False:
            assert_non_statefullness(definition)

        structures = extract_structures(definition)
        for structure in structures:
            if not models.Structure.objects.filter(key=identifier_to_key(structure).lower(), package__key=identifier_to_package_key(structure).lower()).exists():
                raise ValueError(f"Structure {structure} used in ports but not defined in any schema")

        interfaces = extract_interfaces(definition)
        for interface in interfaces:
            if not models.Interface.objects.filter(key=identifier_to_key(interface).lower(), package__key=identifier_to_package_key(interface).lower()).exists():
                raise ValueError(f"Interface {interface} used in ports but not defined in any schema")

        action = models.Action.objects.create(
            hash=hash,
            organization=agent.registry.organization,
            description=definition.description or "No description",
            args=[strawberry.asdict(i) for i in definition.args],
            scope=scope,
            stateful=definition.stateful,
            kind=definition.kind,
            port_groups=[strawberry.asdict(i) for i in definition.port_groups],
            returns=[strawberry.asdict(i) for i in definition.returns],
            name=definition.name,
        )

        create_usages(action, definition)
        protocols = infer_protocols(definition)
        action.protocols.add(*protocols)

        if definition.is_test_for:
            for actionhash in definition.is_test_for:
                action.is_test_for.add(models.Action.objects.get(hash=actionhash))

        if definition.collections:
            for collection_name in definition.collections:
                c, _ = models.Collection.objects.get_or_create(name=collection_name, defaults=dict(creator=agent.registry.user, organization=agent.registry.organization))
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
                dep, _ = models.Dependency.objects.update_or_create(
                    implementation=implementation,
                    key=i.key,
                    defaults=dict(
                        action_hash=i.hash,
                        optional=i.optional,
                        description=i.description,
                        arg_matches=[strawberry.asdict(x) for x in i.arg_matches] if i.arg_matches else [],
                        return_matches=[strawberry.asdict(x) for x in i.return_matches] if i.return_matches else [],
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
                dep, _ = models.Dependency.objects.update_or_create(
                    implementation=implementation,
                    key=i.key,
                    defaults=dict(
                        action_hash=i.hash,
                        optional=i.optional,
                        description=i.description,
                        arg_matches=[strawberry.asdict(x) for x in i.arg_matches] if i.arg_matches else [],
                        return_matches=[strawberry.asdict(x) for x in i.return_matches] if i.return_matches else [],
                    ),
                )
                new_deps.append(dep)

    return implementation


def create_implementation(info: Info, input: inputs.CreateImplementationInput) -> types.Implementation:
    registry, _ = models.Registry.objects.update_or_create(client=info.context.request.client, user=info.context.request.user, organization=info.context.request.organization)

    agent, _ = models.Agent.objects.update_or_create(
        registry=registry,
        instance_id=input.instance_id or "default",
        defaults=dict(
            name=f"{str(registry)} on {input.instance_id}",
        ),
    )

    return _create_implementation(input.implementation, agent, input.extension)


def create_foreign_implementation(info: Info, input: inputs.CreateForeignImplementationInput) -> types.Implementation:
    agent = models.Agent.objects.get(id=input.agent)

    assert input.extension in agent.extensions, f"Extension {input.extension} not supported by agent {agent}"

    return _create_implementation(input.implementation, agent, input.extension)


def delete_implementation(info: Info, input: inputs.DeleteImplementationInput) -> str:
    implementation = models.Implementation.objects.get(id=input.implementation)

    implementation.delete()

    return input.id


def set_extension_implementations(info: Info, input: inputs.SetExtensionImplementationsInput) -> list[types.Implementation]:
    registry, _ = models.Registry.objects.update_or_create(client=info.context.request.client, user=info.context.request.user, organization=info.context.request.organization)

    agent, _ = models.Agent.objects.get_or_create(
        registry=registry,
        instance_id=input.instance_id or "default",
        defaults=dict(
            name=f"{str(registry)} on {input.instance_id}",
        ),
    )

    previous_implementations = models.Implementation.objects.filter(agent=agent, extension=input.extension).all()

    created_implementations_id = []
    created_implementations = []
    for implementation in input.implementations:
        created_implementation = _create_implementation(implementation, agent, input.extension)

        created_implementations_id.append(created_implementation.id)
        created_implementations.append(created_implementation)

    if input.run_cleanup:
        for i in previous_implementations:
            if i.id not in created_implementations_id:
                i.delete()

    return created_implementations


def pin_implementation(info, input: inputs.PinInput) -> types.Implementation:
    user = info.context.request.user

    agent = models.Implementation.objects.get(id=input.id)
    if input.pin:
        agent.pinned_by.add(user)
    else:
        agent.pinned_by.remove(user)
    agent.save()
    return agent
