"""Definitions are validated against the base catalog plus the UI catalog they name at registration."""

from types import SimpleNamespace

import pytest
from authentikate.models import App, Release

from facade import models
from facade.mutations.agent import ImplementAgentInputModel, implement_agent
from rekuest_core.inputs import models as imodels
from tests.factories import create_registry_bundle


def _payload(catalog: str | list[str] | None, operation: str, keys: tuple[str, str] = ("a", "b"), bloks: list[dict] = ()) -> ImplementAgentInputModel:
    first, second = keys
    # ``None`` is what a client sends when it names no catalog; it must mean "base only".
    catalogs = None if catalog is None else [catalog] if isinstance(catalog, str) else list(catalog)
    return ImplementAgentInputModel.model_validate(
        {
            "implementations": [
                {
                    "interface": "scan",
                    "definition": {
                        "key": "scan",
                        "version": "1",
                        "name": "Scan",
                        "kind": "FUNCTION",
                        "catalogs": catalogs,
                        "args": [
                            {
                                "key": "exposure",
                                "kind": "FLOAT",
                                "nullable": False,
                                "validators": [{"call": {"operation": operation, "arguments": [{"key": first, "value_path": "/value"}, {"key": second, "value_literal": 0}]}, "source": f"{operation}(value, 0)"}],
                            }
                        ],
                        "returns": [],
                    },
                }
            ],
            "bloks": list(bloks),
        }
    )


def _call(org, user, client, payload: ImplementAgentInputModel):
    info = SimpleNamespace(context=SimpleNamespace(request=SimpleNamespace(client=client, user=user, organization=org)))
    return implement_agent(info, SimpleNamespace(to_pydantic=lambda: payload))


@pytest.fixture
def tenant():
    user, client, org, _ = create_registry_bundle("def-catalog")
    client.release = Release.objects.create(app=App.objects.create(identifier="def-catalog-app"), version="1.0.0")
    client.save()
    return org, user, client


CLAMP = {"name": "clamp", "arguments": [{"key": "a", "kind": "FLOAT"}, {"key": "b", "kind": "FLOAT"}], "returns": "FLOAT"}


def _register(org, operations: list[dict], components: list[dict] = (), name: str = "electron") -> models.UICatalog:
    return models.UICatalog.objects.create(name=name, organization=org, operations=operations, components=list(components))


def _diagnostics() -> list[dict]:
    return models.Implementation.objects.get().diagnostics


@pytest.mark.django_db
def test_unknown_operation_is_stored_as_a_warning(tenant) -> None:
    """An operation neither base nor the named catalog provides does not block registration."""
    org, user, client = tenant
    _register(org, [CLAMP])

    _call(org, user, client, _payload("electron", "fizz"))
    assert models.Implementation.objects.count() == 1
    (diagnostic,) = _diagnostics()
    assert diagnostic["level"] == "WARNING" and diagnostic["code"] == "unknown_operation"
    assert "'fizz'" in diagnostic["message"] and "base@1 + electron" in diagnostic["message"]


@pytest.mark.django_db
def test_base_and_extension_operations_are_accepted(tenant) -> None:
    """Base (`gt`) and registered (`clamp`) operations both pass without findings."""
    org, user, client = tenant
    _register(org, [CLAMP])

    _call(org, user, client, _payload("electron", "gt"))
    assert _diagnostics() == []
    _call(org, user, client, _payload("electron", "clamp"))
    assert _diagnostics() == []
    assert models.Implementation.objects.count() == 1


@pytest.mark.django_db
def test_base_applies_without_a_catalog(tenant) -> None:
    """No catalog, an unknown catalog name and an empty catalog all validate against base."""
    org, user, client = tenant

    _call(org, user, client, _payload(None, "gt"))
    assert _diagnostics() == []

    _call(org, user, client, _payload("nonexistent", "gt"))
    (diagnostic,) = _diagnostics()
    assert diagnostic["code"] == "unknown_catalog" and "'nonexistent'" in diagnostic["message"]

    models.UICatalog.objects.create(name="empty", organization=org)
    _call(org, user, client, _payload("empty", "gt"))
    assert _diagnostics() == []
    assert models.Implementation.objects.count() == 1


@pytest.mark.django_db
def test_base_argument_mismatch_is_a_hard_error_without_a_catalog(tenant) -> None:
    """Calling a base operation with the wrong argument keys aborts registration."""
    org, user, client = tenant

    with pytest.raises(ValueError, match=r"operation 'between' does not accept arguments \['a', 'b'\]"):
        _call(org, user, client, _payload(None, "between"))
    with pytest.raises(ValueError, match=r"operation 'gt' does not accept arguments \['c'\]"):
        _call(org, user, client, _payload(None, "gt", keys=("a", "c")))
    assert models.Implementation.objects.count() == 0


@pytest.mark.django_db
def test_warning_is_replaced_on_re_registration(tenant) -> None:
    """Registering the catalog later and reconnecting clears the stored warning."""
    org, user, client = tenant

    _call(org, user, client, _payload("electron", "clamp"))
    assert [d["code"] for d in _diagnostics()] == ["unknown_operation", "unknown_catalog"]

    _register(org, [CLAMP])
    _call(org, user, client, _payload("electron", "clamp"))
    assert _diagnostics() == []


@pytest.mark.django_db
def test_agent_declared_bloks_are_validated_against_their_catalog(tenant) -> None:
    """Agent declared bloks are validated against their catalog; unknown util operations become blok warnings."""
    org, user, client = tenant
    _register(org, [], components=[{"name": "Box", "props": [{"key": "v", "kind": "ANY"}]}])
    blok = {"key": "panel", "catalog": "electron", "components": [{"id": "root", "component": "Knob"}]}

    with pytest.raises(ValueError, match="component 'Knob' is not registered"):
        _call(org, user, client, _payload(None, "gt", bloks=[blok]))
    assert models.Blok.objects.count() == 0

    manifest = [{"id": "root", "component": "Box", "props": [{"key": "v", "util_call": {"operation": "fizz"}}]}]
    _call(org, user, client, _payload(None, "gt", bloks=[{**blok, "components": manifest}]))
    stored = models.Blok.objects.get(name="panel")
    assert stored.catalog.name == "electron"
    assert [d["code"] for d in stored.diagnostics] == ["unknown_operation"]


@pytest.mark.django_db
def test_multiple_catalogs_are_unioned_with_base(tenant) -> None:
    """A definition may name several catalogs; base plus all of them are in force."""
    org, user, client = tenant
    _register(org, [CLAMP], name="electron")
    _register(org, [{"name": "fmt", "arguments": [{"key": "a", "kind": "ANY"}, {"key": "b", "kind": "ANY"}], "returns": "STRING"}], name="web")

    _call(org, user, client, _payload(["electron", "web"], "clamp"))
    assert _diagnostics() == []
    _call(org, user, client, _payload(["electron", "web"], "fmt"))
    assert _diagnostics() == []
    _call(org, user, client, _payload(["electron", "web"], "gt"))
    assert _diagnostics() == []
    with pytest.raises(ValueError, match="'fmt' does not accept arguments"):
        _call(org, user, client, _payload(["electron", "web"], "fmt", keys=("x", "y")))


@pytest.mark.django_db
def test_conflicting_catalogs_are_rejected_and_identical_ones_tolerated(tenant) -> None:
    """Two catalogs defining one operation differently cannot be combined; identical copies can."""
    org, user, client = tenant
    _register(org, [CLAMP], name="electron")
    _register(org, [CLAMP], name="twin")
    _register(org, [{**CLAMP, "arguments": [{"key": "v", "kind": "FLOAT"}]}], name="rival")

    _call(org, user, client, _payload(["electron", "twin"], "clamp"))
    assert _diagnostics() == []
    with pytest.raises(ValueError, match="operation 'clamp' is defined differently by catalogs 'electron' and 'rival'"):
        _call(org, user, client, _payload(["electron", "rival"], "clamp"))


@pytest.mark.django_db
def test_base_may_be_named_explicitly(tenant) -> None:
    """``base`` and ``base@1`` are accepted silently; another base version warns; names are deduped."""
    org, user, client = tenant

    _call(org, user, client, _payload(["base", "base@1", "base@1"], "gt"))
    assert _diagnostics() == []
    _call(org, user, client, _payload(["base@2"], "gt"))
    (diagnostic,) = _diagnostics()
    assert diagnostic["code"] == "unknown_catalog" and "base@1" in diagnostic["message"]


# --------------------------------------------------------------------------- widgets


def _widget_payload(catalog: str | None, widget: dict, *, return_widget: dict | None = None, port_kind: str = "FLOAT") -> ImplementAgentInputModel:
    """A definition whose single arg port (and optionally its return port) carries the given widget."""
    catalogs = None if catalog is None else [catalog]
    returns = [{"key": "out", "kind": "STRING", "nullable": False, "widget": return_widget}] if return_widget else []
    identifier = "@x/thing" if port_kind == "STRUCTURE" else None
    return ImplementAgentInputModel.model_validate(
        {
            "implementations": [
                {
                    "interface": "scan",
                    "definition": {
                        "key": "scan",
                        "version": "1",
                        "name": "Scan",
                        "kind": "FUNCTION",
                        "catalogs": catalogs,
                        "args": [{"key": "exposure", "kind": port_kind, "identifier": identifier, "nullable": False, "widget": widget}],
                        "returns": returns,
                    },
                }
            ],
        }
    )


CUSTOM_KNOB = {"kind": "CUSTOM", "component": "Knob", "props": [{"key": "value", "dynamic_value": {"path": "/value"}}]}


@pytest.mark.django_db
def test_custom_widget_component_is_checked_once_the_catalog_registers_components(tenant) -> None:
    """Unknown CUSTOM component: accepted silently without registered components, an error with them."""
    org, user, client = tenant

    _call(org, user, client, _widget_payload(None, CUSTOM_KNOB))
    assert _diagnostics() == []

    _register(org, [], components=[{"name": "Box"}])
    with pytest.raises(ValueError, match="widget of Definition scan port exposure: component 'Knob' is not registered"):
        _call(org, user, client, _widget_payload("electron", CUSTOM_KNOB))
    assert models.Implementation.objects.count() == 1  # the earlier registration survived; nothing new was written

    models.UICatalog.objects.filter(name="electron").update(components=[{"name": "Knob", "props": [{"key": "value", "kind": "FLOAT"}]}])
    _call(org, user, client, _widget_payload("electron", CUSTOM_KNOB))
    assert _diagnostics() == []


@pytest.mark.django_db
def test_widget_calls_are_checked_like_validator_calls(tenant) -> None:
    """Unknown operations in widget props, state pointers and accessors are warnings; key mismatches are errors."""
    org, user, client = tenant

    custom = {"kind": "CUSTOM", "component": "Knob", "props": [{"key": "label", "util_call": {"operation": "fizz"}}]}
    _call(org, user, client, _widget_payload(None, custom))
    (diagnostic,) = _diagnostics()
    assert diagnostic["code"] == "unknown_operation" and "widget of Definition scan port exposure" in diagnostic["path"]

    state = {"kind": "STATE_CHOICE", "state_call": {"operation": "buzz"}, "state_accessors": [{"option_key": "LABEL", "call": {"operation": "fizz"}}]}
    _call(org, user, client, _widget_payload(None, state))
    assert [d["code"] for d in _diagnostics()] == ["unknown_operation", "unknown_operation"]

    wrong_keys = {"kind": "CUSTOM", "component": "Knob", "props": [{"key": "label", "util_call": {"operation": "gt", "arguments": [{"key": "left", "value_path": "/value"}]}}]}
    with pytest.raises(ValueError, match=r"operation 'gt' does not accept arguments \['left'\]"):
        _call(org, user, client, _widget_payload(None, wrong_keys))


@pytest.mark.django_db
def test_filter_ports_fallbacks_and_return_widgets_are_walked(tenant) -> None:
    """Widgets nested in SEARCH filter ports, in fallback chains and on return ports are all validated."""
    org, user, client = tenant
    _register(org, [], components=[{"name": "Box"}])

    query = "query S($search: String, $values: [ID!], $f: String) { x }"
    in_filter = {"kind": "SEARCH", "query": query, "ward": "mikro", "filters": [{"key": "f", "kind": "STRING", "nullable": False, "widget": CUSTOM_KNOB}]}
    with pytest.raises(ValueError, match="widget of Definition scan port exposure filter port f: component 'Knob'"):
        _call(org, user, client, _widget_payload("electron", in_filter, port_kind="STRUCTURE"))

    in_fallback = {**CUSTOM_KNOB, "component": "Box", "props": [], "fallback": CUSTOM_KNOB}
    with pytest.raises(ValueError, match="widget of Definition scan port exposure fallback 1: component 'Knob'"):
        _call(org, user, client, _widget_payload("electron", in_fallback))

    with pytest.raises(ValueError, match="widget of Definition scan port out: component 'Gauge'"):
        _call(org, user, client, _widget_payload("electron", {"kind": "SLIDER"}, return_widget={"kind": "CUSTOM", "component": "Gauge"}))
    assert models.Implementation.objects.count() == 0


@pytest.mark.django_db
def test_optimistic_pointer_calls_are_checked(tenant) -> None:
    """An optimistic path_call naming an unknown operation is a warning on the implementation."""
    org, user, client = tenant
    payload = _widget_payload(None, {"kind": "SLIDER"})
    payload.implementations[0].optimistics = [imodels.OptimisticInputModel(state="stage", path_call={"operation": "fizz", "arguments": [{"key": "a", "value_path": "/args/axis"}]})]

    _call(org, user, client, payload)
    (diagnostic,) = _diagnostics()
    assert diagnostic["code"] == "unknown_operation" and "'fizz'" in diagnostic["message"]
