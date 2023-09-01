from typing import NewType
import strawberry

FlowHash = strawberry.scalar(
    NewType("FlowHash", str),
    description="The `ArrayLike` scalasr typsse represents a reference to a store "
    "previously created by the user n a datalayer",
    serialize=lambda v: v,
    parse_value=lambda v: v,
)


ValueMap = strawberry.scalar(
    NewType("ValueMap", object),
    description="The `ArrayLike` scalasr typsse represents a reference to a store "
    "previously created by the user n a datalayer",
    serialize=lambda v: v,
    parse_value=lambda v: v,
)
