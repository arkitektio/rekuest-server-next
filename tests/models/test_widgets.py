"""Kind-aware widget inputs, custom widgets as catalog components, state accessors, optimistics and windows."""

import pytest
from pydantic import ValidationError

from rekuest_core.inputs import models as imodels
from rekuest_core.objects import models as omodels


def _widget(kind: str, **fields: object) -> imodels.AssignWidgetInputModel:
    return imodels.AssignWidgetInputModel(kind=kind, **fields)


@pytest.mark.parametrize(
    ("kind", "fields"),
    [
        ("SEARCH", {"query": "query { x }", "ward": "mikro", "filters": None, "dependencies": ["other"], "placeholder": "pick"}),
        ("CHOICE", {"choices": [{"value": "a", "label": "A"}], "placeholder": "pick"}),
        ("SLIDER", {"min": 0, "max": 10, "step": 1}),
        ("SLIDER", {}),
        ("STRING", {"placeholder": "type", "as_paragraph": True}),
        ("CUSTOM", {"component": "Knob", "dependencies": ["other"], "props": [{"key": "value", "dynamic_value": {"path": "/value"}}], "fallback": {"kind": "STRING"}}),
        ("STATE_CHOICE", {"state_path": "/positions", "dependency": "stage", "state_accessors": [{"option_key": "LABEL", "path": "/name"}]}),
        ("STATE_CHOICE", {"state_call": {"operation": "pick", "arguments": [{"key": "s", "value_path": "/state/positions"}]}}),
        ("PROXY", {"target_port": "image", "target_action": "acquire", "target_dependency": "camera"}),
    ],
)
def test_each_kind_accepts_its_own_fields(kind: str, fields: dict) -> None:
    """Each kind accepts its own fields."""
    _widget(kind, **fields)


@pytest.mark.parametrize(
    ("kind", "fields", "message"),
    [
        ("SEARCH", {"ward": "mikro"}, "SEARCH widget requires ['query']"),
        ("SEARCH", {"query": "q", "ward": "w", "min": 1}, "must not set ['min']"),
        ("CHOICE", {"choices": []}, "CHOICE widget requires ['choices']"),
        ("SLIDER", {"state_path": "/x"}, "must not set ['state_path']"),
        ("STRING", {"component": "Knob"}, "must not set ['component']"),
        ("CUSTOM", {}, "CUSTOM widget requires ['component']"),
        ("STATE_CHOICE", {}, "exactly one of state_path or state_call"),
        ("STATE_CHOICE", {"state_path": "/x", "state_call": {"operation": "pick"}}, "exactly one of state_path or state_call"),
        ("PROXY", {"target_port": "image"}, "PROXY widget requires ['target_action']"),
    ],
)
def test_wrong_fields_for_a_kind_are_rejected(kind: str, fields: dict, message: str) -> None:
    """Wrong fields for a kind are rejected."""
    with pytest.raises(ValidationError, match=__import__("re").escape(message)):
        _widget(kind, **fields)


def test_custom_widget_props_must_be_pure_and_scoped() -> None:
    """Custom widget props must be pure and scoped."""
    with pytest.raises(ValidationError, match="agent calls are not allowed in widgets"):
        _widget("CUSTOM", component="Knob", props=[{"key": "onClick", "agent_call": {"dependency": "stage", "operation": "move"}}])
    with pytest.raises(ValidationError, match="references 'other' via dynamic_value.path"):
        _widget("CUSTOM", component="Knob", props=[{"key": "x", "dynamic_value": {"path": "/other/v"}}])
    with pytest.raises(ValidationError, match="references 'other' via value_path"):
        _widget("CUSTOM", component="Knob", props=[{"key": "x", "util_call": {"operation": "fmt", "arguments": [{"key": "v", "value_path": "/other/v"}]}}])
    _widget("CUSTOM", component="Knob", dependencies=["other"], props=[{"key": "x", "util_call": {"operation": "fmt", "arguments": [{"key": "v", "value_path": "/other/v"}]}}])


def test_state_choice_calls_may_reference_state_but_not_undeclared_ports() -> None:
    """State choice calls may reference state but not undeclared ports."""
    with pytest.raises(ValidationError, match="references 'other'"):
        _widget("STATE_CHOICE", state_call={"operation": "pick", "arguments": [{"key": "s", "value_path": "/other"}]})
    _widget("STATE_CHOICE", dependencies=["other"], state_call={"operation": "pick", "arguments": [{"key": "s", "value_path": "/other"}, {"key": "t", "value_path": "/state/x"}]})
    with pytest.raises(ValidationError, match="StateAccessor 0 references 'other'"):
        _widget("STATE_CHOICE", state_path="/x", state_accessors=[{"option_key": "LABEL", "call": {"operation": "f", "arguments": [{"key": "v", "value_path": "/other"}]}}])


def test_state_accessor_is_static_or_computed() -> None:
    """State accessor is static or computed."""
    with pytest.raises(ValidationError, match="either path or call"):
        imodels.StateAccessorInputModel(option_key="LABEL", path="/x", call={"operation": "f"})
    imodels.StateAccessorInputModel(option_key="LABEL")


def test_custom_widgets_round_trip_to_output_models() -> None:
    """Custom widgets round trip to output models."""
    arg = imodels.ArgPortInputModel(
        key="foo",
        kind="STRING",
        nullable=False,
        widget=_widget("CUSTOM", component="Knob", dependencies=["bar"], props=[{"key": "value", "dynamic_value": {"path": "/value"}}], fallback={"kind": "STRING"}),
    )
    out = omodels.ArgPortModel(**arg.model_dump())
    assert isinstance(out.widget, omodels.CustomAssignWidgetModel)
    assert out.widget.component == "Knob"
    assert out.widget.props[0].dynamic_value.path == "/value"
    assert isinstance(out.widget.fallback, omodels.StringWidgetModel)

    ret = imodels.ReturnPortInputModel(key="out", kind="STRING", nullable=False, widget={"kind": "CUSTOM", "component": "Gauge"})
    out = omodels.ReturnPortModel(**ret.model_dump())
    assert isinstance(out.widget, omodels.CustomReturnWidgetModel)
    assert out.widget.kind == "CUSTOM"


def test_return_widget_kind_matrix() -> None:
    """Return widget kind matrix."""
    with pytest.raises(ValidationError, match="CHOICE return widget requires"):
        imodels.ReturnWidgetInputModel(kind="CHOICE")
    with pytest.raises(ValidationError, match="must not set"):
        imodels.ReturnWidgetInputModel(kind="CHOICE", choices=[{"value": "a", "label": "A"}], component="X")
    with pytest.raises(ValidationError, match="agent calls are not allowed"):
        imodels.ReturnWidgetInputModel(kind="CUSTOM", component="X", props=[{"key": "k", "agent_call": {"dependency": "d", "operation": "o"}}])


def test_custom_effect_carries_only_its_call() -> None:
    """Custom effect carries only its call."""
    effect = imodels.EffectInputModel(kind="CUSTOM", call={"operation": "shake"}, dependencies=[])
    assert set(effect.model_dump()) == {"kind", "call", "dependencies", "message", "fade"}


def test_optimistic_pointer_is_static_or_computed_from_args() -> None:
    """Optimistic pointer is static or computed from args."""
    imodels.OptimisticInputModel(state="stage", path="/position")
    imodels.OptimisticInputModel(state="stage", path_call={"operation": "sel", "arguments": [{"key": "a", "value_path": "/args/axis"}]})
    with pytest.raises(ValidationError, match="exactly one of path or path_call"):
        imodels.OptimisticInputModel(state="stage")
    with pytest.raises(ValidationError, match="references 'state'"):
        imodels.OptimisticInputModel(state="stage", path_call={"operation": "sel", "arguments": [{"key": "a", "value_path": "/state/x"}]})


def test_window_function_is_an_enum() -> None:
    """Window function is an enum."""
    with pytest.raises(ValidationError):
        imodels.WindowInputModel(window_function="average")
    window = imodels.WindowInputModel(window_function="MEAN", label="avg")
    track = omodels.TrackModel(state_key="s", value_key="v", windows=[window.model_dump()])
    assert track.windows[0].window_function == "MEAN"
