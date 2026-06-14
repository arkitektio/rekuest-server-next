from typing import NewType
import strawberry


MediaLike = NewType("MediaLike", str)
ArrayLike = NewType("ArrayLike", list)


scalar_map = {
    MediaLike: strawberry.scalar(
        name="MediaLike",
        description="A type representing a media store reference, which can be either a string ID or a more complex object.",
        serialize=lambda v: v,  # Implement your serialization logic here
        parse_value=lambda v: v,  # Implement your parsing logic here
    ),
    ArrayLike: strawberry.scalar(
        name="ArrayLike",
        description="A type representing an array-like structure, which can be a list or any iterable.",
        serialize=lambda v: v,  # Implement your serialization logic here
        parse_value=lambda v: v,  # Implement your parsing logic here
    ),
}
