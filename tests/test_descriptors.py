"""Unit tests for the requires/provides -> PostgreSQL JSONPath compiler.

These are pure (no database): they assert the compiled JSONPath strings that later get
evaluated by ``jsonb_path_match`` at query time.
"""

from types import SimpleNamespace

import pytest

from facade.descriptors import compile_descriptors_to_jsonpath


def d(key, operator, value):
    return SimpleNamespace(key=key, operator=operator, value=value)


def test_empty_descriptors_returns_none():
    assert compile_descriptors_to_jsonpath(None) is None
    assert compile_descriptors_to_jsonpath([]) is None


def test_equals_and_matches_render_equality():
    assert compile_descriptors_to_jsonpath([d("axes", "EQUALS", "c")]) == '$.axes == "c"'
    assert compile_descriptors_to_jsonpath([d("axes", "MATCHES", "c")]) == '$.axes == "c"'


def test_not_equals():
    assert compile_descriptors_to_jsonpath([d("axes", "NOT_EQUALS", "c")]) == '$.axes != "c"'


def test_numeric_comparisons():
    assert compile_descriptors_to_jsonpath([d("size", "GTE", 10)]) == "$.size >= 10"
    assert compile_descriptors_to_jsonpath([d("size", "LTE", 10)]) == "$.size <= 10"


def test_exists_true_and_false():
    assert compile_descriptors_to_jsonpath([d("axes", "EXISTS", True)]) == "exists($.axes)"
    assert compile_descriptors_to_jsonpath([d("axes", "EXISTS", False)]) == "!(exists($.axes))"


def test_contains_array_membership():
    assert compile_descriptors_to_jsonpath([d("tags", "CONTAINS", "brain")]) == '$.tags[*] == "brain"'


def test_in_and_not_in_expand_to_boolean_combinations():
    assert compile_descriptors_to_jsonpath([d("axes", "IN", ["c", "t"])]) == '($.axes == "c" || $.axes == "t")'
    assert compile_descriptors_to_jsonpath([d("axes", "NOT_IN", ["c", "t"])]) == '($.axes != "c" && $.axes != "t")'


def test_in_requires_a_list_value():
    with pytest.raises(ValueError):
        compile_descriptors_to_jsonpath([d("axes", "IN", "c")])


def test_multiple_descriptors_are_anded():
    compiled = compile_descriptors_to_jsonpath([d("axes", "EQUALS", "c"), d("dtype", "EQUALS", "uint8")])
    assert compiled == '$.axes == "c" && $.dtype == "uint8"'


def test_dotted_key_is_normalised():
    assert compile_descriptors_to_jsonpath([d("options.advanced", "EQUALS", 1)]) == "$.options.advanced == 1"
    # Already-rooted keys are not double-prefixed.
    assert compile_descriptors_to_jsonpath([d("$.axes", "EQUALS", "c")]) == '$.axes == "c"'


def test_invalid_key_is_rejected_to_prevent_jsonpath_injection():
    with pytest.raises(ValueError):
        compile_descriptors_to_jsonpath([d('axes" == "c" || $.x', "EQUALS", "c")])
    with pytest.raises(ValueError):
        compile_descriptors_to_jsonpath([d("axes; drop", "EQUALS", "c")])


def test_unsupported_operator_raises():
    with pytest.raises(ValueError):
        compile_descriptors_to_jsonpath([d("axes", "NONSENSE", "c")])
