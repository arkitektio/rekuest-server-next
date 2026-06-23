"""Unit tests for the pure caller-event mapper (no DB, no channels).

``build_caller_message`` is the single place that turns a persisted ``AssignationEvent``
into its minimal caller-bound socket message, so it is exercised here with a light stub.
"""

from dataclasses import dataclass
from typing import Optional

import pytest

from facade import messages
from facade.caller_events import build_caller_message
from facade.enums import AssignationEventChoices as Kind


@dataclass
class StubEvent:
    """The minimal surface ``build_caller_message`` reads — stands in for the ORM model."""

    id: int = 42
    assignation_id: str = "ass-1"
    kind: str = Kind.PROGRESS.value
    message: Optional[str] = None
    progress: Optional[int] = None
    returns: Optional[dict] = None
    level: Optional[str] = None


def test_progress_maps_with_progress_and_message():
    msg = build_caller_message(StubEvent(kind=Kind.PROGRESS.value, progress=50, message="half"))
    assert isinstance(msg, messages.CallerProgress)
    assert msg.assignation == "ass-1" and msg.event == "42" and msg.seq == 42
    assert msg.progress == 50 and msg.message == "half"


def test_yield_carries_returns():
    msg = build_caller_message(StubEvent(kind=Kind.YIELD.value, returns={"x": 1}))
    assert isinstance(msg, messages.CallerYield) and msg.returns == {"x": 1}


def test_error_and_critical_take_message_as_error():
    err = build_caller_message(StubEvent(kind=Kind.ERROR.value, message="boom"))
    crit = build_caller_message(StubEvent(kind=Kind.CRITICAL.value, message="fatal"))
    assert isinstance(err, messages.CallerError) and err.error == "boom"
    assert isinstance(crit, messages.CallerCritical) and crit.error == "fatal"


def test_log_defaults_invalid_level_to_info():
    # AssignationEvent.level is an AssignationEventChoices string (or None) — not a log
    # level — so a non-log-level value must degrade to INFO rather than fail validation.
    info = build_caller_message(StubEvent(kind=Kind.LOG.value, message="hi", level=None))
    assert isinstance(info, messages.CallerLog) and info.level == "INFO" and info.message == "hi"
    warn = build_caller_message(StubEvent(kind=Kind.LOG.value, message="hi", level="WARN"))
    assert isinstance(warn, messages.CallerLog) and warn.level == "WARN"
    coerced = build_caller_message(StubEvent(kind=Kind.LOG.value, level="PROGRESS"))
    assert isinstance(coerced, messages.CallerLog) and coerced.level == "INFO"


def test_disconnected_carries_message():
    msg = build_caller_message(StubEvent(kind=Kind.DISCONNECTED.value, message="fate unknown"))
    assert isinstance(msg, messages.CallerDisconnected) and msg.message == "fate unknown"


@pytest.mark.parametrize(
    "kind,cls",
    [
        (Kind.BOUND.value, messages.CallerBound),
        (Kind.QUEUED.value, messages.CallerQueued),
        (Kind.ASSIGN.value, messages.CallerAssigned),
        (Kind.DELEGATE.value, messages.CallerDelegate),
        (Kind.DONE.value, messages.CallerDone),
        (Kind.CANCELING.value, messages.CallerCanceling),
        (Kind.CANCELLED.value, messages.CallerCancelled),
        (Kind.INTERUPTING.value, messages.CallerInterrupting),
        (Kind.INTERUPTED.value, messages.CallerInterrupted),
        (Kind.PAUSING.value, messages.CallerPausing),
        (Kind.PAUSED.value, messages.CallerPaused),
        (Kind.RESUMING.value, messages.CallerResuming),
        (Kind.RESUMED.value, messages.CallerResumed),
    ],
)
def test_bare_kinds_map_to_their_class(kind, cls):
    msg = build_caller_message(StubEvent(kind=kind))
    assert isinstance(msg, cls)
    assert msg.assignation == "ass-1" and msg.event == "42" and msg.seq == 42


def test_interupted_is_a_plain_string_value_not_a_tuple():
    # Guards the confusing `INTERUPTED = ("INTERUPTED",)` literal in AssignationEventKind:
    # the persisted choices value must be a plain string so the mapping matches.
    assert Kind.INTERUPTED.value == "INTERUPTED"
    assert isinstance(build_caller_message(StubEvent(kind="INTERUPTED")), messages.CallerInterrupted)


def test_unforwarded_kind_returns_none():
    assert build_caller_message(StubEvent(kind="UNASSIGN")) is None
