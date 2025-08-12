from typing import Any, NewType

import strawberry


@strawberry.scalar(description="The `Args` scalar type represents a Dictionary of arguments")
class Args(object):
    """Strawberry scalar for Args type representing a dictionary of arguments."""

    @staticmethod
    def serialize(value: Any) -> Any:
        """Serialize an Args value for output."""
        return value

    @staticmethod
    def parse_value(value: Any) -> "Args":
        """Parse input value into Args type."""
        return value


@strawberry.scalar(description="The `SearchQuery` scalar type represents a search query string")
class SearchQuery(str):
    """Strawberry scalar for SearchQuery type representing a search query string."""

    @staticmethod
    def serialize(value: Any) -> str:
        """Serialize a SearchQuery value for output."""
        return str(value)

    @staticmethod
    def parse_value(value: str) -> str:
        """Parse input value into SearchQuery type."""
        return value


@strawberry.scalar(description="The `InstanceID` scalar type represents a unique instance identifier")
class InstanceID(str):
    """Strawberry scalar for InstanceID type representing a unique instance identifier."""

    @staticmethod
    def serialize(value: Any) -> str:
        """Serialize an InstanceID value for output."""
        return str(value)

    @staticmethod
    def parse_value(value: str) -> str:
        """Parse input value into InstanceID type."""
        return value
