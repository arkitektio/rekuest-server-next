"""Validate blok manifests and port calls against a registered UI catalog.

A ``UICatalog`` a UI app has registered lists the components it can render and the pure
operations it can evaluate. When a blok (or an action definition) names such a catalog, every
``ComponentNode.component``, ``ComponentProp.key`` and ``UtilCall.operation`` it uses must exist
there. A catalog that was only ever created by ``get_or_create`` (nothing registered) validates
nothing, so registration keeps working before the UI app has announced itself.
"""

from typing import Iterable, Iterator

from facade import models
from rekuest_core.inputs import models as rimodels
from rekuest_core.inputs.models import iter_component_nodes, iter_util_calls


def _check_call(call: rimodels.UtilCallInputModel, operations: dict[str, rimodels.CatalogOperationInputModel], catalog: models.UICatalog, owner: str) -> None:
    spec = operations.get(call.operation)
    if spec is None:
        raise ValueError(f"{owner}: operation {call.operation!r} is not registered in catalog {catalog.name!r}")
    accepted = {argument.key: argument for argument in spec.arguments}
    passed = {argument.key for argument in call.arguments or []}
    unknown = sorted(passed - set(accepted))
    if unknown:
        raise ValueError(f"{owner}: operation {call.operation!r} does not accept arguments {unknown}")
    missing = sorted(key for key, argument in accepted.items() if argument.required and key not in passed)
    if missing:
        raise ValueError(f"{owner}: operation {call.operation!r} requires arguments {missing}")


def validate_calls_against_catalog(catalog: models.UICatalog, calls: Iterable[rimodels.UtilCallInputModel], owner: str) -> None:
    """Every call (and every call nested in its arguments) names a registered operation with matching argument keys."""
    if not catalog.is_registered:
        return
    operations = {operation.name: operation for operation in catalog.get_operations()}
    for call in calls:
        _check_call(call, operations, catalog, owner)
        for nested in iter_util_calls(call.arguments):
            _check_call(nested, operations, catalog, owner)


def validate_manifest_against_catalog(catalog: models.UICatalog, components: list[rimodels.ComponentNodeInputModel] | None) -> None:
    """Every component, prop and operation a blok manifest uses is registered in ``catalog``."""
    if not catalog.is_registered:
        return
    component_specs = {component.name: component for component in catalog.get_components()}
    operations = {operation.name: operation for operation in catalog.get_operations()}

    for node in iter_component_nodes(components):
        owner = f"component {node.id!r}"
        spec = component_specs.get(node.component)
        if spec is None:
            raise ValueError(f"{owner}: component {node.component!r} is not registered in catalog {catalog.name!r}")
        if node.children and not spec.accepts_children:
            raise ValueError(f"{owner}: component {node.component!r} does not accept children")

        prop_specs = {prop.key: prop for prop in spec.props}
        present = {prop.key for prop in node.props or []}
        unknown = sorted(present - set(prop_specs))
        if unknown:
            raise ValueError(f"{owner}: component {node.component!r} has no props {unknown}")
        missing = sorted(key for key, prop in prop_specs.items() if prop.required and key not in present)
        if missing:
            raise ValueError(f"{owner}: component {node.component!r} requires props {missing}")

        for prop in node.props or []:
            prop_owner = f"prop {prop.key!r} of {owner}"
            if prop_specs[prop.key].kind == rimodels.enums.CatalogValueKind.CALLBACK and prop.agent_call is None and prop.util_call is None:
                raise ValueError(f"{prop_owner} is a CALLBACK prop and must be bound via agent_call or util_call")
            for call in _prop_calls(prop):
                _check_call(call, operations, catalog, prop_owner)


def _prop_calls(prop: rimodels.ComponentPropInputModel) -> Iterator[rimodels.UtilCallInputModel]:
    if prop.util_call is not None:
        yield prop.util_call
        yield from iter_util_calls(prop.util_call.arguments)
    if prop.agent_call is not None:
        yield from iter_util_calls(prop.agent_call.arguments)


def iter_definition_calls(definition: rimodels.DefinitionInputModel) -> Iterator[rimodels.UtilCallInputModel]:
    """Every effect and validator call of a definition: args, returns, nested children, port groups."""

    def walk(ports: list[rimodels.PortInputModel]) -> Iterator[rimodels.UtilCallInputModel]:
        for port in ports:
            for validator in port.validators or []:
                yield validator.call
            for effect in port.effects or []:
                yield effect.call
            yield from walk(port.children or [])

    yield from walk(definition.args)
    yield from walk(definition.returns)
    for group in definition.port_groups or []:
        for effect in group.effects or []:
            yield effect.call


def catalog_for_definition(definition: rimodels.DefinitionInputModel, agent: models.Agent) -> models.UICatalog | None:
    """The catalog a definition opted into, if it exists in the agent's organization."""
    if not definition.catalog:
        return None
    return models.UICatalog.objects.filter(name=definition.catalog, organization=agent.organization).first()
