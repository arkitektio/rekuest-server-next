"""Unit tests for the higher-order projection logic (pure; no DB / no stack)."""

import pytest

from facade.higher_order import (
    build_lower_args,
    build_lower_dependencies,
    project_returns,
    validate_dependency_coverage,
)


class TestBuildLowerArgs:
    def test_default_bound_spread_plus_reified_args(self):
        config = {"bound": {"model": "resnet50"}, "args_key": "args"}
        caller = {"image": 1, "threshold": 0.5}

        result = build_lower_args(config, caller)

        assert result == {"model": "resnet50", "args": {"image": 1, "threshold": 0.5}}

    def test_explicit_arg_map_renames_and_consumes(self):
        # 'image' is lifted to a named lower port; only the remainder is reified.
        config = {
            "bound": {"model": "resnet50"},
            "args_key": "args",
            "arg_map": {"input_image": {"from": "caller", "key": "image"}},
        }
        caller = {"image": 1, "threshold": 0.5}

        result = build_lower_args(config, caller)

        assert result == {"model": "resnet50", "input_image": 1, "args": {"threshold": 0.5}}

    def test_no_args_key_spreads_remaining(self):
        config = {"bound": {"model": "x"}}
        caller = {"a": 1, "b": 2}

        result = build_lower_args(config, caller)

        assert result == {"model": "x", "a": 1, "b": 2}

    def test_missing_mapped_caller_arg_raises(self):
        config = {"arg_map": {"lp": {"from": "caller", "key": "missing"}}}
        with pytest.raises(ValueError):
            build_lower_args(config, {"present": 1})


class TestBuildLowerDependencies:
    def test_empty_map_passes_through_by_key(self):
        h_deps = {"gpu": [{"agent": "a1"}]}
        assert build_lower_dependencies({}, h_deps) == {"gpu": [{"agent": "a1"}]}

    def test_explicit_map_caller_and_bound(self):
        config = {
            "dependency_map": {
                "renderer": {"from": "caller", "key": "gpu"},
                "store": {"from": "bound", "value": [{"agent": "fixed"}]},
            }
        }
        h_deps = {"gpu": [{"agent": "a1"}]}

        result = build_lower_dependencies(config, h_deps)

        assert result == {"renderer": [{"agent": "a1"}], "store": [{"agent": "fixed"}]}

    def test_missing_caller_dependency_raises(self):
        config = {"dependency_map": {"renderer": {"from": "caller", "key": "gpu"}}}
        with pytest.raises(ValueError):
            build_lower_dependencies(config, {})

    def test_bad_source_raises(self):
        config = {"dependency_map": {"renderer": {"from": "nonsense"}}}
        with pytest.raises(ValueError):
            build_lower_dependencies(config, {})


class TestProjectReturns:
    def test_none_returns_stay_none(self):
        assert project_returns({}, None) is None

    def test_identity_when_no_return_map(self):
        assert project_returns({}, {"out": 5}) == {"out": 5}

    def test_explicit_return_map_renames(self):
        config = {"return_map": {"prediction": "out", "score": "confidence"}}
        lower = {"out": 5, "confidence": 0.9, "ignored": 1}

        assert project_returns(config, lower) == {"prediction": 5, "score": 0.9}


class TestValidateDependencyCoverage:
    def test_passthrough_ok_when_keys_declared(self):
        validate_dependency_coverage({}, lower_dependency_keys=["gpu"], declared_h_dependency_keys=["gpu"])

    def test_passthrough_missing_declared_raises(self):
        with pytest.raises(ValueError):
            validate_dependency_coverage({}, lower_dependency_keys=["gpu"], declared_h_dependency_keys=[])

    def test_explicit_map_uncovered_lower_dep_raises(self):
        config = {"dependency_map": {"renderer": {"from": "bound", "value": []}}}
        with pytest.raises(ValueError):
            validate_dependency_coverage(config, lower_dependency_keys=["renderer", "store"], declared_h_dependency_keys=[])

    def test_undeclared_caller_source_raises(self):
        config = {"dependency_map": {"renderer": {"from": "caller", "key": "gpu"}}}
        with pytest.raises(ValueError):
            validate_dependency_coverage(config, lower_dependency_keys=["renderer"], declared_h_dependency_keys=[])

    def test_fully_covered_explicit_map_ok(self):
        config = {
            "dependency_map": {
                "renderer": {"from": "caller", "key": "gpu"},
                "store": {"from": "bound", "value": []},
            }
        }
        validate_dependency_coverage(config, lower_dependency_keys=["renderer", "store"], declared_h_dependency_keys=["gpu"])
