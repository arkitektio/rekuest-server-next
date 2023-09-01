from typing import NewType
import strawberry

Identifier = strawberry.scalar(
    NewType("Identifier", str),
    description="The `ArrayLike` scalar type represents a reference to a store "
    "previously created by the user n a datalayer",
    serialize=lambda v: v,
    parse_value=lambda v: v,
)

AnyDefault = strawberry.scalar(
    NewType("AnyDefault", object),
    description="The `ArrayLike` scalar type represents a reference to a store "
    "previously created by the user n a datalayer",
    serialize=lambda v: v,
    parse_value=lambda v: v,
)

Arg = strawberry.scalar(
    NewType("Arg", object),
    description="The `Arg` scalar type represents a an Argument in a Node assignment",
    serialize=lambda v: v,
    parse_value=lambda v: v,
)

SearchQuery = strawberry.scalar(
    NewType("SearchQuery", str),
    description="The `ArrayLike` scalar type represents a reference to a store "
    "previously created by the user n a datalayer",
    serialize=lambda v: v,
    parse_value=lambda v: v,
)

InstanceID = strawberry.scalar(
    NewType("InstanceId", str),
    description="The `ArrayLike` scalar type represents a reference to a store "
    "previously created by the user n a datalayer",
    serialize=lambda v: v,
    parse_value=lambda v: v,
)

NodeHash = strawberry.scalar(
    NewType("NodeHash", str),
    description="The `ArrayLike` scalar type represents a reference to a store "
    "previously created by the user n a datalayer",
    serialize=lambda v: v,
    parse_value=lambda v: v,
)
