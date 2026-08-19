"""Smoke test: the GraphQL schema must build and render to a non-empty SDL string.

No database required — this only imports and stringifies the schema.
"""

import re

from facade.schema import schema


def test_print_schema():
    sdl = str(schema)
    print(sdl)  # visible with `pytest -s`
    assert sdl.strip(), "Schema SDL should not be empty"


def test_no_phantom_column_ordering_keys():
    """Guard against the ``status``/``startedAt`` class of bug returning.

    ``strawberry_django.order_type`` never validates its annotations against the model, so an
    ordering key naming a nonexistent column builds a perfectly valid SDL and only raises
    ``FieldError`` at query time. ``TaskStatus`` had no backing column and no consumer at all.
    """
    sdl = str(schema)
    assert "TaskStatus" not in sdl

    # ``Session`` genuinely has started_at/ended_at — SessionOrder is the legitimate original
    # these two were copy-pasted from, so scope the assertion to the offending inputs.
    for input_name in ("TaskOrder", "ImplementationOrder"):
        block = re.search(rf"input {input_name} [^{{]*\{{[^}}]*\}}", sdl)
        assert block, f"{input_name} missing from the SDL"
        for phantom in ("startedAt", "finishedAt", "status"):
            if input_name == "TaskOrder" and phantom == "finishedAt":
                continue  # Task really does have finished_at
            assert phantom not in block.group(0), f"{input_name}.{phantom} names a nonexistent column"
