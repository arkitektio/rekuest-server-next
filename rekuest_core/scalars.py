from typing import NewType
import strawberry

Identifier = NewType("Identifier", str)
JSONSerializable = NewType("JSONSerializable", object)
AnyDefault = NewType("AnyDefault", object)
Arg = NewType("Arg", object)
SearchQuery = NewType("SearchQuery", str)
InstanceID = NewType("InstanceID", str)
ActionHash = NewType("ActionHash", str)
ValidatorFunction = NewType("ValidatorFunction", object)


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
        description="The `ArrayLike` scalar type represents a reference to a store previously created by the user n a datalayer",
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
    ValidatorFunction: strawberry.scalar(
        name="ValidatorFunction",
        description="""
    The `Validator` scalar represents a javascript function that should execute on the client side (inside a shadow realm)
      to validate a value (or a set of values) before it is sent to the server.  The function has two parameters (value, otherValues) and should return a string if the value is invalid and undefined if the value is valid.
        The otherValues parameter is an object with the other values in the form {fieldName: value}.""",
        serialize=lambda v: v,
        parse_value=lambda v: v,
    ),
}
