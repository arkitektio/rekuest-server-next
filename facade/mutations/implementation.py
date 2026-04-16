import hashlib
import json
import logging

import strawberry
from facade import inputs, models, types
from facade.protocol import infer_protocols
from facade.unique import assert_non_statefullness, infer_action_scope
from kante.types import Info
from rekuest_core.inputs.models import ArgPortInputModel, DefinitionInputModel, ImplementationInputModel, PortInputModel, RequiresInputModel, ProvidesInputModel, ReturnPortInputModel
from rekuest_core.enums import PortKind, ProvidesOperator, RequiresOperator
from authentikate.vars import get_user, get_client
import typing as t

logger = logging.getLogger(__name__)


def hash_definition(definition: DefinitionInputModel) -> str:
    hashable_definition = {
        key: value
        for key, value in dict(definition.model_dump()).items()
        if key
        in [
            "name",
            "description",
            "args",
            "returns",
            "stateful",
            "is_test_for",
            "collections",
            "dependencies",
            "key",
            "version",
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


def compile_descriptors_to_jsonpath(descriptors: list[RequiresInputModel] | None) -> str | None:
    """
    Translates Pydantic descriptor models into a valid PostgreSQL JSONPath string.
    Returns None if no descriptors exist, which allows Django to save NULL to the DB.
    """
    if not descriptors:
        return None

    path_conditions = []

    for desc in descriptors:
        # Standardize the key path (e.g., 'axes.c' becomes '$.axes.c')
        # If they already put '$.', don't duplicate it.
        pg_path = desc.key if desc.key.startswith("$.") else f"$.{desc.key}"

        # PRO-TIP: json.dumps natively formats Python True to 'true',
        # strings to '"string"', and ints to '1' (Perfect for JSONPath).
        formatted_val = json.dumps(desc.value)

        # Extract string value from enum (handles both standard Enum and Django TextChoices)
        op = desc.operator

        # Map the operators to PG JSONPath Syntax
        if op == RequiresOperator.MATCHES:
            # In PG JSONPath, exists() returns a boolean based on path existence.
            # We check if the user asked for exists=True or exists=False
            if desc.value is True:
                path_conditions.append(f"exists({pg_path})")
            else:
                path_conditions.append(f"!(exists({pg_path}))")

        elif op == RequiresOperator.MATCHES:
            path_conditions.append(f"{pg_path} == {formatted_val}")

        elif op == RequiresOperator.EQUALS:
            path_conditions.append(f"{pg_path} == {formatted_val}")

        elif op == RequiresOperator.NOT_EQUALS:
            path_conditions.append(f"{pg_path} != {formatted_val}")

        elif op == RequiresOperator.GTE:
            path_conditions.append(f"{pg_path} >= {formatted_val}")

        elif op == RequiresOperator.LTE:
            path_conditions.append(f"{pg_path} <= {formatted_val}")

        elif op == RequiresOperator.CONTAINS:
            # JSONPath array inclusion. e.g., $.tags[*] == "brain"
            path_conditions.append(f"{pg_path}[*] == {formatted_val}")

        elif op == RequiresOperator.IN:
            # JSONPath array inclusion. e.g., $.tags[*] IN ["brain", "neural"]
            path_conditions.append(f"{pg_path} IN {formatted_val}")

        else:
            raise ValueError(f"Unsupported JSONPath operator: {op}")

    # Join all the constraints using the logical AND operator for JSONPath
    return " && ".join(path_conditions)


def compile_returndescriptors_to_jsonpath(descriptors: list[ProvidesInputModel] | None) -> str | None:
    """
    Translates Pydantic descriptor models into a valid PostgreSQL JSONPath string.
    Returns None if no descriptors exist, which allows Django to save NULL to the DB.
    """
    if not descriptors:
        return None

    path_conditions = []

    for desc in descriptors:
        # Standardize the key path (e.g., 'axes.c' becomes '$.axes.c')
        # If they already put '$.', don't duplicate it.
        pg_path = desc.key if desc.key.startswith("$.") else f"$.{desc.key}"

        # PRO-TIP: json.dumps natively formats Python True to 'true',
        # strings to '"string"', and ints to '1' (Perfect for JSONPath).
        formatted_val = json.dumps(desc.value)

        # Extract string value from enum (handles both standard Enum and Django TextChoices)
        op = desc.operator

        # Map the operators to PG JSONPath Syntax
        if op == ProvidesOperator.EXISTS:
            # In PG JSONPath, exists() returns a boolean based on path existence.
            # We check if the user asked for exists=True or exists=False
            if desc.value is True:
                path_conditions.append(f"exists({pg_path})")
            else:
                path_conditions.append(f"!(exists({pg_path}))")

        elif op == ProvidesOperator.MATCHES:
            path_conditions.append(f"{pg_path} == {formatted_val}")

        elif op == ProvidesOperator.EQUALS:
            path_conditions.append(f"{pg_path} == {formatted_val}")

        elif op == ProvidesOperator.NOT_EQUALS:
            path_conditions.append(f"{pg_path} != {formatted_val}")

        elif op == ProvidesOperator.GTE:
            path_conditions.append(f"{pg_path} >= {formatted_val}")

        elif op == ProvidesOperator.LTE:
            path_conditions.append(f"{pg_path} <= {formatted_val}")

        elif op == ProvidesOperator.CONTAINS:
            # JSONPath array inclusion. e.g., $.tags[*] == "brain"
            path_conditions.append(f"{pg_path}[*] == {formatted_val}")

        else:
            raise ValueError(f"Unsupported JSONPath operator: {op}")

    # Join all the constraints using the logical AND operator for JSONPath
    return " && ".join(path_conditions)


# =========================================================
# 2. THE RECURSIVE PORT EXTRACTOR (The Relational Engine Builder)
# =========================================================
def extract_ports_recursively(
    port_data: ArgPortInputModel,
    action_instance: models.Action,  # The saved Action Django model instance to link to
    parent_instance: t.Any = None,  # The saved Parent Port Django model (if nested)
    index: int = 0,
    parent_path: str = "",  # The semantic materialized string path
) -> None:
    """
    Recursively flattens the Pydantic tree into relational DB objects.
    Because of the `parent` ForeignKey, we MUST save the parent to the database
    first to get its ID before we can save its children.
    """

    # 1. Build the Semantic Materialized Path (e.g., "options.advanced.mask")
    current_path = f"{parent_path}.{port_data.key}" if parent_path else port_data.key

    # 2. Extract Descriptors safely (children might be base PortInputModels without requires/provides)
    descriptors = getattr(port_data, "requires", None) or getattr(port_data, "provides", None) or []
    compiled_path = compile_descriptors_to_jsonpath(descriptors)

    # 3. Create and Save the Current Port
    current_port = models.ArgPort(
        action=action_instance, parent=parent_instance, index=index, key=port_data.key, key_path=current_path, kind=port_data.kind.value if hasattr(port_data.kind, "value") else port_data.kind, identifier=port_data.identifier, compiled_jsonpath=compiled_path, nullable=port_data.nullable
    )

    # The Write-Time Hit: We save immediately to get the Primary Key (ID)
    current_port.save()

    # 4. Recurse for Children (e.g., items inside a LIST or properties of a DICT/STRUCTURE)
    if port_data.children:
        for child_idx, child_data in enumerate(port_data.children):
            extract_ports_recursively(
                port_data=child_data,
                action_instance=action_instance,
                parent_instance=current_port,  # Link the child to this newly saved port
                index=child_idx,
                parent_path=current_path,  # Pass the materialized path down
            )


# =========================================================
# 2. THE RECURSIVE PORT EXTRACTOR (The Relational Engine Builder)
# =========================================================
def extract_returnports_recursively(
    port_data: ReturnPortInputModel,
    action_instance: models.Action,  # The saved Action Django model instance to link to
    parent_instance: t.Any = None,  # The saved Parent Port Django model (if nested)
    index: int = 0,
    parent_path: str = "",  # The semantic materialized string path
) -> None:
    """
    Recursively flattens the Pydantic tree into relational DB objects.
    Because of the `parent` ForeignKey, we MUST save the parent to the database
    first to get its ID before we can save its children.
    """

    # 1. Build the Semantic Materialized Path (e.g., "options.advanced.mask")
    current_path = f"{parent_path}.{port_data.key}" if parent_path else port_data.key

    # 2. Extract Descriptors safely (children might be base PortInputModels without requires/provides)
    descriptors = getattr(port_data, "requires", None) or getattr(port_data, "provides", None) or []
    compiled_path = compile_returndescriptors_to_jsonpath(descriptors)

    # 3. Create and Save the Current Port
    current_port = models.ReturnPort(
        action=action_instance, parent=parent_instance, index=index, key=port_data.key, key_path=current_path, kind=port_data.kind.value if hasattr(port_data.kind, "value") else port_data.kind, identifier=port_data.identifier, compiled_jsonpath=compiled_path, nullable=port_data.nullable
    )

    # The Write-Time Hit: We save immediately to get the Primary Key (ID)
    current_port.save()

    # 4. Recurse for Children (e.g., items inside a LIST or properties of a DICT/STRUCTURE)
    if port_data.children:
        for child_idx, child_data in enumerate(port_data.children):
            extract_returnports_recursively(
                port_data=child_data,
                action_instance=action_instance,
                parent_instance=current_port,  # Link the child to this newly saved port
                index=child_idx,
                parent_path=current_path,  # Pass the materialized path down
            )


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


def _create_implementation(input: ImplementationInputModel, agent: models.Agent) -> models.Implementation:
    definition = input.definition

    hash = hash_definition(definition)
    key = definition.key
    version = definition.version
    app = agent.app or models.Action.objects.get_or_create(identifier=input.definition.app, organization=agent.organization)[0]

    scope = infer_action_scope(definition)

    if definition.stateful is False:
        assert_non_statefullness(definition)

    try:
        action = models.Action.objects.get(key=key, version=version, app=app, organization=agent.organization)
        if action.hash != hash:
            print("We are in the update flow, but the hash is different. This means the definition has changed. We need to check if the app matches to prevent malicious updates.")
            if action.app == agent.app:
                action.hash = hash
                action.args = [i.model_dump() for i in definition.args]
                action.returns = [i.model_dump() for i in definition.returns]
                action.stateful = definition.stateful
                action.scope = scope
                action.kind = definition.kind
                action.description = definition.description or "No description"
                action.name = definition.name
                action.save()
            else:
                raise ValueError(f"Action with key {key} and version {version} already exists but has different hash and you are not the owner. Please update the version or key of your action definition.")
    except models.Action.DoesNotExist:
        action = models.Action.objects.create(
            key=key,
            version=version,
            app=app,
            hash=hash,
            organization=agent.registry.organization,
            description=definition.description or "No description",
            args=[i.model_dump() for i in definition.args],
            scope=scope,
            stateful=definition.stateful,
            kind=definition.kind,
            port_groups=[i.model_dump() for i in definition.port_groups],
            returns=[i.model_dump() for i in definition.returns],
            name=definition.name,
        )

    # 2. Build the Relational ArgPorts (The Micro-Filtering Engine)
    if definition.args:
        for idx, arg in enumerate(definition.args):
            extract_ports_recursively(port_data=arg, action_instance=action, index=idx)

    # 3. Build the Relational ReturnPorts (The Micro-Filtering Engine)
    if definition.returns:
        for idx, ret in enumerate(definition.returns):
            extract_returnports_recursively(port_data=ret, action_instance=action, index=idx)

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

        if implementation.action.pk != action.pk:
            if implementation.action.implementations.count() == 1:
                logger.info("Deleting Action because it has no more implementations")
                implementation.action.delete()

        implementation.action = action
        implementation.params = input.params or {}
        implementation.release = agent.registry.client.release
        implementation.save()

        new_deps = []

        if input.dependencies:
            for i in input.dependencies:
                dep, _ = models.Dependency.objects.update_or_create(
                    implementation=implementation,
                    key=i.key,
                    defaults=dict(
                        action_demands=[x.model_dump() for x in i.action_demands] if i.action_demands else [],
                        app_filter=i.app,
                        version_filter=i.version,
                    ),
                )
                new_deps.append(dep)

    except models.Implementation.DoesNotExist:
        implementation = models.Implementation.objects.create(
            interface=input.interface,
            release=agent.registry.client.release,
            action=action,
            agent=agent,
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
                        action_demands=[x.model_dump() for x in i.action_demands] if i.action_demands else [],
                        app_filter=i.app,
                        version_filter=i.version,
                        min_viable_instances=i.min_viable_instances,
                        max_viable_instances=i.max_viable_instances,
                        prefered_instances=i.prefered_instances,
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
            name=f"{str(registry.pk)} on {input.instance_id}",
            release=info.context.request.client.release,
            app=info.context.request.client.release.app,
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


def pin_implementation(info: Info, input: inputs.PinInput) -> types.Implementation:
    user = info.context.request.user

    agent = models.Implementation.objects.get(id=input.id)
    if input.pin:
        agent.pinned_by.add(user)
    else:
        agent.pinned_by.remove(user)
    agent.save()
    return agent
