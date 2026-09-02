"""UI catalog registry: registration, tenant isolation, and validation of bloks against it."""

import pytest
from asgiref.sync import sync_to_async
from kante.context import HttpContext

from facade.models import UICatalog
from facade.schema import schema
from tests.graphql.test_cross_tenant_isolation import OTHER_TOKEN, tenant_context
from tests.graphql_ops import CREATE_BLOK

REGISTER_UI_CATALOG = """
    mutation RegisterUiCatalog($input: RegisterUiCatalogInput!) {
        registerUiCatalog(input: $input) {
            id
            name
            description
            isRegistered
            components { name props { key kind required } acceptsChildren }
            operations { name arguments { key kind required } returns }
        }
    }
"""

UI_CATALOGS = "query { uiCatalogs { id name } }"
UI_CATALOG = "query UiCatalog($id: ID!) { uiCatalog(id: $id) { id name } }"

CATALOG = {
    "name": "electron",
    "description": "The desktop app",
    "components": [
        {"name": "Slider", "props": [{"key": "value", "kind": "FLOAT", "required": True}, {"key": "onChange", "kind": "CALLBACK"}], "acceptsChildren": False},
        {"name": "Box"},
    ],
    "operations": [
        {"name": "gt", "arguments": [{"key": "a", "kind": "FLOAT"}, {"key": "b", "kind": "FLOAT"}], "returns": "BOOL"},
        {"name": "fmt", "arguments": [{"key": "v", "kind": "ANY"}], "returns": "STRING"},
    ],
}


async def _register(context: HttpContext, catalog: dict = CATALOG) -> dict:
    result = await schema.execute(REGISTER_UI_CATALOG, context_value=context, variable_values={"input": catalog})
    assert not result.errors, result.errors
    return result.data["registerUiCatalog"]


async def _create_blok(context: HttpContext, components: list[dict], catalog: str = "electron", **extra: object):
    return await schema.execute(
        CREATE_BLOK,
        context_value=context,
        variable_values={"input": {"name": "catalogued", "catalog": catalog, "components": components, "demoState": {"exposure": 1}, **extra}},
    )


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestUiCatalog:
    async def test_register_upserts_by_name_within_the_organization(self, authenticated_context: HttpContext) -> None:
        """Registering twice under one name updates the same row and replaces its contents."""
        first = await _register(authenticated_context)
        assert first["isRegistered"] is True
        assert {c["name"] for c in first["components"]} == {"Slider", "Box"}
        assert first["components"][0]["props"][0] == {"key": "value", "kind": "FLOAT", "required": True}
        assert first["operations"][0]["returns"] == "BOOL"

        second = await _register(authenticated_context, {**CATALOG, "components": [{"name": "Text"}], "operations": []})
        assert second["id"] == first["id"]
        assert [c["name"] for c in second["components"]] == ["Text"]
        assert second["operations"] == []
        assert await sync_to_async(UICatalog.objects.filter(name="electron").count)() == 1

    async def test_catalogs_are_scoped_to_the_organization(self, authenticated_context: HttpContext) -> None:
        """Another organization may register the same name and neither sees the other's catalog."""
        other, _, _, _ = await sync_to_async(tenant_context)(OTHER_TOKEN)

        mine = await _register(authenticated_context)
        theirs = await _register(other)
        assert mine["id"] != theirs["id"]

        listed = await schema.execute(UI_CATALOGS, context_value=authenticated_context)
        assert not listed.errors, listed.errors
        assert {row["id"] for row in listed.data["uiCatalogs"]} == {mine["id"]}

        foreign = await schema.execute(UI_CATALOG, context_value=authenticated_context, variable_values={"id": theirs["id"]})
        assert foreign.errors, "org A read org B's catalog"

    async def test_blok_against_registered_catalog_is_validated(self, authenticated_context: HttpContext) -> None:
        """Unknown components, props and operations are rejected; a conforming manifest is accepted."""
        await _register(authenticated_context)

        unknown_component = await _create_blok(authenticated_context, [{"id": "root", "component": "Knob"}])
        assert unknown_component.errors and "component 'Knob' is not registered" in unknown_component.errors[0].message

        unknown_prop = await _create_blok(authenticated_context, [{"id": "root", "component": "Slider", "props": [{"key": "value", "staticValue": 1}, {"key": "colour", "staticValue": "red"}]}])
        assert unknown_prop.errors and "has no props ['colour']" in unknown_prop.errors[0].message

        missing_required = await _create_blok(authenticated_context, [{"id": "root", "component": "Slider"}])
        assert missing_required.errors and "requires props ['value']" in missing_required.errors[0].message

        children_refused = await _create_blok(authenticated_context, [{"id": "root", "component": "Slider", "props": [{"key": "value", "staticValue": 1}], "children": [{"id": "c", "component": "Box"}]}])
        assert children_refused.errors and "does not accept children" in children_refused.errors[0].message

        unknown_operation = await _create_blok(
            authenticated_context,
            [{"id": "root", "component": "Slider", "props": [{"key": "value", "utilCall": {"operation": "clamp", "arguments": [{"key": "v", "valuePath": "/exposure"}]}}]}],
        )
        assert unknown_operation.errors and "operation 'clamp' is not registered" in unknown_operation.errors[0].message

        wrong_arguments = await _create_blok(
            authenticated_context,
            [{"id": "root", "component": "Slider", "props": [{"key": "value", "utilCall": {"operation": "gt", "arguments": [{"key": "a", "valuePath": "/exposure"}]}}]}],
        )
        assert wrong_arguments.errors and "requires arguments ['b']" in wrong_arguments.errors[0].message

        accepted = await _create_blok(
            authenticated_context,
            [
                {
                    "id": "root",
                    "component": "Box",
                    "children": [
                        {
                            "id": "slider",
                            "component": "Slider",
                            "props": [
                                {"key": "value", "utilCall": {"operation": "gt", "arguments": [{"key": "a", "valuePath": "/exposure"}, {"key": "b", "valueLiteral": 0}]}},
                                {"key": "onChange", "utilCall": {"operation": "fmt", "arguments": [{"key": "v", "valuePath": "/exposure"}]}},
                            ],
                        }
                    ],
                }
            ],
        )
        assert not accepted.errors, accepted.errors

    async def test_unregistered_catalog_validates_nothing(self, authenticated_context: HttpContext) -> None:
        """A catalog that only exists because a blok named it does not reject anything."""
        result = await _create_blok(authenticated_context, [{"id": "root", "component": "Whatever", "props": [{"key": "x", "utilCall": {"operation": "anything"}}]}], catalog="fresh")
        assert not result.errors, result.errors
