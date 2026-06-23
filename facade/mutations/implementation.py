import hashlib
import json
import logging

import strawberry
from facade import inputs, models, types
from facade.descriptors import compile_descriptors_to_jsonpath, compile_returndescriptors_to_jsonpath
from facade.protocol import infer_protocols
from facade.unique import assert_non_statefullness, infer_action_scope
from kante.types import Info
from rekuest_core.inputs.models import ArgPortInputModel, DefinitionInputModel, ImplementationInputModel, PortInputModel, ReturnPortInputModel
from rekuest_core.enums import PortKind
from rekuest_core import scalars as rscalars
from authentikate.vars import get_user, get_client
from facade.higher_order import validate_dependency_coverage, validate_higher_order_pairing
from facade.provenance import audience as provenance_audience
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


def extract_interfaces_recursively(interfaces: list[str], definition: PortInputModel):
    if definition.identifier and definition.kind == PortKind.INTERFACE:
        interfaces.append(definition.identifier)

    for port in definition.children or []:
        extract_interfaces_recursively(interfaces, port)


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

    # 2. Extract the input-side descriptors (children might be base PortInputModels without requires)
    descriptors = getattr(port_data, "requires", None) or []
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

    # 2. Extract the output-side descriptors (children might be base PortInputModels without provides)
    descriptors = getattr(port_data, "provides", None) or []
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
        package, _ = models.StructurePackage.objects.get_or_create(key=identifier_to_package_key(port.identifier).lower())

        structure, _ = models.Structure.objects.get_or_create(key=identifier_to_key(port.identifier).lower(), package=package)

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
        interface, _ = models.Interface.objects.get_or_create(key=identifier_to_key(port.identifier).lower(), package__key=identifier_to_package_key(port.identifier).lower())

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
        package, _ = models.StructurePackage.objects.get_or_create(key=identifier_to_package_key(port.identifier).lower())

        structure, _ = models.Structure.objects.get_or_create(key=identifier_to_key(port.identifier).lower(), package=package)

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
        interface, _ = models.Interface.objects.get_or_create(key=identifier_to_key(port.identifier).lower(), package__key=identifier_to_package_key(port.identifier).lower())

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


def rebuild_relational_ports(action: models.Action, definition: DefinitionInputModel) -> None:
    """Replace the relational ArgPort/ReturnPort rows for ``action`` from its definition.

    Existing rows are deleted first because this runs on every (re)registration; without
    the purge, reconnecting agents would accumulate duplicate ports that the matching layer
    would then double-count. Also refreshes the pre-calculated root-port counts on the Action.
    """
    # CASCADE on the self-referential ``parent`` FK removes nested children too.
    action.arg_ports.all().delete()
    action.return_ports.all().delete()

    for idx, arg in enumerate(definition.args or []):
        extract_ports_recursively(port_data=arg, action_instance=action, index=idx)

    for idx, ret in enumerate(definition.returns or []):
        extract_returnports_recursively(port_data=ret, action_instance=action, index=idx)

    action.arg_count = len(definition.args or [])
    action.return_count = len(definition.returns or [])
    action.save(update_fields=["arg_count", "return_count"])


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
            organization=agent.organization,
            description=definition.description or "No description",
            args=[i.model_dump() for i in definition.args],
            scope=scope,
            stateful=definition.stateful,
            kind=definition.kind,
            port_groups=[i.model_dump() for i in definition.port_groups],
            returns=[i.model_dump() for i in definition.returns],
            name=definition.name,
        )

    # 2. (Re)build the relational ArgPort/ReturnPort rows (The Micro-Filtering Engine that
    #    the matching layer queries). This runs on every (re)registration, so we must clear
    #    the previous rows first to avoid accumulating duplicate/stale ports.
    rebuild_relational_ports(action, definition)

    create_usages(action, definition)
    protocols = infer_protocols(definition)
    action.protocols.add(*protocols)

    if definition.is_test_for:
        for actionhash in definition.is_test_for:
            action.is_test_for.add(models.Action.objects.get(hash=actionhash))

    if definition.collections:
        for collection_name in definition.collections:
            c, _ = models.Collection.objects.get_or_create(name=collection_name, defaults=dict(creator=agent.user, organization=agent.organization))
            action.collections.add(c)

    logger.info(f"Created {action}")
    action.save()

    # Resolve the provenance audience once, at registration: an explicit declaration
    # wins, otherwise derive it from the action's structure ports (e.g. @mikro/image
    # -> mikro). Persisted on the implementation so dispatch never recomputes it.
    if input.provenance_audience is not None:
        resolved_audience = input.provenance_audience
    else:
        resolved_audience = provenance_audience.derive_from_action(action) or None

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
        implementation.release = agent.release
        implementation.needs_token = input.needs_token
        implementation.provenance_audience = resolved_audience
        implementation.effect = getattr(input.effect, "value", input.effect)
        implementation.save()

        new_deps = []

        if input.dependencies:
            for i in input.dependencies:
                dep, _ = models.Dependency.objects.update_or_create(
                    implementation=implementation,
                    key=i.key,
                    defaults=dict(
                        action_demands=[x.model_dump() for x in i.action_demands] if i.action_demands else [],
                        state_demands=[x.model_dump() for x in i.state_demands] if i.state_demands else [],
                        app_filter=i.app,
                        version_filter=i.version,
                    ),
                )
                new_deps.append(dep)

        if input.manipulates:
            print("Updating manipulates for implementation", implementation.pk, input.manipulates)
            states = models.State.objects.filter(agent=agent, interface__in=input.manipulates)
            implementation.manipulates.set(states)

        if input.tracks:
            implementation.tracks = [t.model_dump() for t in input.tracks]
            implementation.save()

    except models.Implementation.DoesNotExist:
        implementation = models.Implementation.objects.create(
            interface=input.interface,
            release=agent.release,
            action=action,
            agent=agent,
            dynamic=input.dynamic,
            params=input.params or {},
            needs_token=input.needs_token,
            provenance_audience=resolved_audience,
            effect=getattr(input.effect, "value", input.effect),
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
                        auto_resolvable=i.auto_resolvable,
                    ),
                )
                new_deps.append(dep)

        if input.manipulates:
            print("Updating manipulates for implementation", implementation.pk, input.manipulates)
            states = models.State.objects.filter(agent=agent, interface__in=input.manipulates)
            implementation.manipulates.set(states)

        if input.tracks:
            implementation.tracks = [t.model_dump() for t in input.tracks]
            implementation.save()

    return implementation


def create_implementation(info: Info, input: inputs.CreateImplementationInput) -> types.Implementation:
    agent, _ = models.Agent.objects.update_or_create(
        client=info.context.request.client,
        user=info.context.request.user,
        organization=info.context.request.organization,
        defaults=dict(
            name=f"{info.context.request.client.client_id}",
            release=info.context.request.client.release,
            app=info.context.request.client.release.app,
        ),
    )

    return _create_implementation(input.implementation, agent)


@strawberry.input(description="Mark an existing implementation as a higher-order wrapper of a lower implementation.")
class SetHigherOrderInput:
    implementation: strawberry.ID = strawberry.field(description="The wrapper implementation to mark as higher-order.")
    lower_implementation: strawberry.ID = strawberry.field(description="The lower implementation it wraps.")
    config: rscalars.AnyDefault | None = strawberry.field(default=None, description="Projection config: bound params + arg/dependency/return maps (see Implementation.higher_order_config).")


def set_higher_order(info: Info, input: SetHigherOrderInput) -> types.Implementation:
    """Link a wrapper implementation to the lower implementation it wraps, with a projection config.

    Validates the pairing up front: no self-wrap, no nested wrappers, the action kinds must agree,
    and every lower dependency slot must be covered by a bound dep or one of the wrapper's *declared*
    dependencies (so the caller knows what to pass).
    """
    higher = models.Implementation.objects.get(id=input.implementation)
    lower = models.Implementation.objects.get(id=input.lower_implementation)

    if higher.pk == lower.pk:
        raise ValueError("An implementation cannot wrap itself")

    # A higher-order implementation is always bound to the agent that owns the lower
    # implementation it wraps — the wrapper is virtual and its child runs on that agent.
    # Cross-agent wrapping is not supported: register the wrapper on the lower's agent.
    if higher.agent_id != lower.agent_id:
        raise ValueError("A higher-order implementation must be on the same agent as the lower implementation it wraps. Register the wrapper on the lower implementation's agent.")

    config = input.config or {}

    validate_higher_order_pairing(
        higher.action.kind,
        lower.action.kind,
        lower_is_higher_order=lower.higher_order_for_id is not None,
    )
    validate_dependency_coverage(
        config,
        lower_dependency_keys=[d.key for d in lower.dependencies.all()],
        declared_h_dependency_keys=[d.key for d in higher.dependencies.all()],
    )

    higher.higher_order_for = lower
    higher.higher_order_config = config
    higher.save()
    return higher


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
