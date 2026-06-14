from typing import NewType

import strawberry


Args = NewType("Args", object)
UISchema = NewType("UISchema", object)
Props = NewType("Props", object)
SearchQuery = NewType("SearchQuery", str)
InstanceId = NewType("InstanceId", str)


scalar_map = {
    Args: strawberry.scalar(
        name="Args",
        description="The `Args` scalar type represents a Dictionary of arguments",
        serialize=lambda v: v,
        parse_value=lambda v: v,
    ),
    UISchema: strawberry.scalar(
        name="UISchema",
        description="The `Args` scalar type represents a Dictionary of arguments",
        serialize=lambda v: v,
        parse_value=lambda v: v,
    ),
    Props: strawberry.scalar(
        name="Props",
        description="The `Args` scalar type represents a Dictionary of arguments",
        serialize=lambda v: v,
        parse_value=lambda v: v,
    ),
    SearchQuery: strawberry.scalar(
        name="SearchQuery",
        description="The `SearchQuery` scalar type represents a search query string",
        serialize=lambda v: str(v),
        parse_value=lambda v: v,
    ),
    InstanceId: strawberry.scalar(
        name="InstanceId",
        description="The `InstanceID` scalar type represents a unique instance identifier",
        serialize=lambda v: str(v),
        parse_value=lambda v: v,
    ),
}
