from typing import NewType
import strawberry

Identifier = NewType("Identifier", str)
JSONSerializable = NewType("JSONSerializable", object)
AnyDefault = NewType("AnyDefault", object)
Arg = NewType("Arg", object)
SearchQuery = NewType("SearchQuery", str)
InstanceID = NewType("InstanceID", str)
ActionHash = NewType("ActionHash", str)


scalar_map = {
    Identifier: strawberry.scalar(
        name="Identifier",
        description="The `ArrayLike` scalar type represents a reference to a store previously created by the user n a datalayer",
        serialize=lambda v: v,
        parse_value=lambda v: v,
    ),
    JSONSerializable: strawberry.scalar(
        name="JSONSerializable",
        description="The `JSONSerializable` scalar type represents a JSON-serializable value.",
        serialize=lambda v: v,
        parse_value=lambda v: v,
    ),
    AnyDefault: strawberry.scalar(
        name="AnyDefault",
        description="The `ArrayLike` scalar type represents a reference to a store previously created by the user n a datalayer",
        serialize=lambda v: v,
        parse_value=lambda v: v,
    ),
    Arg: strawberry.scalar(
        name="Arg",
        description="The `Arg` scalar type represents a an Argument in a Action assignment",
        serialize=lambda v: v,
        parse_value=lambda v: v,
    ),
    SearchQuery: strawberry.scalar(
        name="SearchQuery",
        description="The `SearchQuery` scalar is a GraphQL query string a search widget executes against its ward to populate its choices",
        serialize=lambda v: v,
        parse_value=lambda v: v,
    ),
    InstanceID: strawberry.scalar(
        name="InstanceId",
        description="The `ArrayLike` scalar type represents a reference to a store previously created by the user n a datalayer",
        serialize=lambda v: v,
        parse_value=lambda v: v,
    ),
    ActionHash: strawberry.scalar(
        name="ActionHash",
        description="The `ArrayLike` scalar type represents a reference to a store previously created by the user n a datalayer",
        serialize=lambda v: v,
        parse_value=lambda v: v,
    ),
}
