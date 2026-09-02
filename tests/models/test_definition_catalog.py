"""Definitions that name a UI catalog have their effect/validator calls checked against it at registration."""

from types import SimpleNamespace

import pytest
from authentikate.models import App, Release

from facade import models
from facade.mutations.agent import ImplementAgentInputModel, implement_agent
from tests.factories import create_registry_bundle


def _payload(catalog: str | None, operation: str, bloks: list[dict] = ()) -> ImplementAgentInputModel:
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
                        "catalog": catalog,
                        "args": [
                            {
                                "key": "exposure",
                                "kind": "FLOAT",
                                "nullable": False,
                                "validators": [{"call": {"operation": operation, "arguments": [{"key": "a", "value_path": "/value"}, {"key": "b", "value_literal": 0}]}}],
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


def _register(org, operations: list[dict], components: list[dict] = ()) -> models.UICatalog:
    return models.UICatalog.objects.create(name="electron", organization=org, operations=operations, components=list(components))


@pytest.mark.django_db
def test_unknown_operation_is_rejected_when_the_catalog_is_registered(tenant) -> None:
    """Unknown operation is rejected when the catalog is registered."""
    org, user, client = tenant
    _register(org, [{"name": "gt", "arguments": [{"key": "a", "kind": "FLOAT"}, {"key": "b", "kind": "FLOAT"}], "returns": "BOOL"}])

    with pytest.raises(ValueError, match="operation 'between' is not registered in catalog 'electron'"):
        _call(org, user, client, _payload("electron", "between"))
    assert models.Implementation.objects.count() == 0


@pytest.mark.django_db
def test_registered_operation_is_accepted(tenant) -> None:
    """Registered operation is accepted."""
    org, user, client = tenant
    _register(org, [{"name": "gt", "arguments": [{"key": "a", "kind": "FLOAT"}, {"key": "b", "kind": "FLOAT"}], "returns": "BOOL"}])

    _call(org, user, client, _payload("electron", "gt"))
    assert models.Implementation.objects.count() == 1


@pytest.mark.django_db
def test_unknown_or_unregistered_catalog_skips_the_check(tenant) -> None:
    """Unknown or unregistered catalog skips the check."""
    org, user, client = tenant

    _call(org, user, client, _payload("nonexistent", "between"))
    _call(org, user, client, _payload(None, "between"))
    models.UICatalog.objects.create(name="empty", organization=org)
    _call(org, user, client, _payload("empty", "between"))
    assert models.Implementation.objects.count() == 1


@pytest.mark.django_db
def test_agent_declared_bloks_are_validated_against_their_catalog(tenant) -> None:
    """Agent declared bloks are validated against their catalog."""
    org, user, client = tenant
    _register(org, [], components=[{"name": "Box"}])
    blok = {"key": "panel", "catalog": "electron", "components": [{"id": "root", "component": "Knob"}]}

    with pytest.raises(ValueError, match="component 'Knob' is not registered"):
        _call(org, user, client, _payload(None, "gt", bloks=[blok]))
    assert models.Blok.objects.count() == 0

    _call(org, user, client, _payload(None, "gt", bloks=[{**blok, "components": [{"id": "root", "component": "Box"}]}]))
    assert models.Blok.objects.get(name="panel").catalog.name == "electron"
