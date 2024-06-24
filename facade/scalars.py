from typing import NewType

import strawberry



Args = strawberry.scalar(
    NewType("Args", object),
    description="The `Args` scalar type represents a Dictionary of arguments",
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

