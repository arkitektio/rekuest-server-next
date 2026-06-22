"""Map a persisted ``AssignationEvent`` to its caller-bound socket message.

The calling participant (the one that originated work via ``CallerAssign``) receives a
minimal per-kind ``Caller*`` mirror of each assignation event over its own socket — no
GraphQL. This module is the single, pure, DB-free place that decides which ``Caller*``
class an event kind maps to and how its fields are populated, so it is trivially
unit-testable with a light event-like stub.

``seq`` and ``event`` both derive from the event's primary key on purpose: ``event`` is a
stable dedup handle, ``seq`` the monotonic ordering / gap-detection key.
"""

from __future__ import annotations

from typing import Optional, Protocol, cast

from facade import messages
from facade.enums import AssignationEventChoices as Kind

_LOG_LEVELS = {"DEBUG", "INFO", "ERROR", "WARN", "CRITICAL"}


class EventLike(Protocol):
    """The minimal surface ``build_caller_message`` reads — satisfied by the ORM model and test stubs."""

    id: int
    assignation_id: int
    kind: object  # a TextChoices/str-enum member or a plain string; normalized in build_caller_message
    message: Optional[str]
    progress: Optional[int]
    returns: Optional[dict]
    level: Optional[str]


def _base_kwargs(event: EventLike) -> dict:
    return {
        "assignation": str(event.assignation_id),
        "event": str(event.id),
        "seq": int(event.id),
    }


def build_caller_message(event: EventLike) -> Optional[messages.CallerEventMessage]:
    """Build the ``Caller*`` message mirroring ``event``, or ``None`` if its kind is not forwarded.

    Keys off the persisted ``kind`` string (``AssignationEventChoices`` values). Unknown /
    not-forwarded kinds (e.g. ``UNASSIGN``) return ``None`` so the caller stream stays minimal.
    """
    base = _base_kwargs(event)
    # ``event.kind`` may be a TextChoices/str-enum member (whose ``str()`` is "Cls.NAME") or a
    # plain string depending on how the row was built/loaded — normalize to the raw value.
    kind = event.kind.value if hasattr(event.kind, "value") else str(event.kind)

    if kind == Kind.PROGRESS.value:
        return messages.CallerProgress(**base, progress=event.progress, message=event.message)
    if kind == Kind.YIELD.value:
        return messages.CallerYield(**base, returns=event.returns)
    if kind == Kind.LOG.value:
        level = event.level if event.level in _LOG_LEVELS else "INFO"
        return messages.CallerLog(**base, message=event.message, level=cast(messages.LogLevelLiteral, level))
    if kind == Kind.ERROR.value:
        return messages.CallerError(**base, error=event.message)
    if kind == Kind.CRITICAL.value:
        return messages.CallerCritical(**base, error=event.message)
    if kind == Kind.DISCONNECTED.value:
        return messages.CallerDisconnected(**base, message=event.message)
    if kind == Kind.DONE.value:
        return messages.CallerDone(**base)
    if kind == Kind.BOUND.value:
        return messages.CallerBound(**base)
    if kind == Kind.QUEUED.value:
        return messages.CallerQueued(**base)
    if kind == Kind.ASSIGN.value:
        return messages.CallerAssigned(**base)
    if kind == Kind.DELEGATE.value:
        return messages.CallerDelegate(**base)
    if kind == Kind.CANCELING.value:
        return messages.CallerCanceling(**base)
    if kind == Kind.CANCELLED.value:
        return messages.CallerCancelled(**base)
    if kind == Kind.INTERUPTING.value:
        return messages.CallerInterrupting(**base)
    if kind == Kind.INTERUPTED.value:
        return messages.CallerInterrupted(**base)
    if kind == Kind.PAUSING.value:
        return messages.CallerPausing(**base)
    if kind == Kind.PAUSED.value:
        return messages.CallerPaused(**base)
    if kind == Kind.RESUMING.value:
        return messages.CallerResuming(**base)
    if kind == Kind.RESUMED.value:
        return messages.CallerResumed(**base)
    if kind == Kind.STEPPING.value:
        return messages.CallerStepping(**base)
    if kind == Kind.STEPPED.value:
        return messages.CallerStepped(**base)
    return None
