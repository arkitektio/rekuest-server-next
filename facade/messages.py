"""Messages that are used to communicate between the rekuest backend and the agent"""

from typing import Any, List, Optional, Literal, Union, Dict
from pydantic import BaseModel, ConfigDict
from enum import Enum
from pydantic import Field
import uuid


JSONSerializable = Union[str, int, float, bool, None, dict[str, "JSONSerializable"], list["JSONSerializable"]]


ShallowJSONSerializable = Union[str, int, float, bool, None, dict[str, Any], list[Any]]  # type: ignore

LogLevelLiteral = Literal[
    "DEBUG",
    "INFO",
    "ERROR",
    "WARN",
    "CRITICAL",
]


class LogLevel(str, Enum):
    """No documentation"""

    DEBUG = "DEBUG"
    INFO = "INFO"
    ERROR = "ERROR"
    WARN = "WARN"
    CRITICAL = "CRITICAL"


class AgentMode(str, Enum):
    """How a participant intends to use the single agent protocol.

    The mode is requested on ``Register`` but only *granted* if the token carries the
    matching capability scopes (see ``facade.capabilities``). It maps onto the two
    independent capability axes ``executes_work`` and ``can_assign_root``:

    - ``EXECUTOR``     — runs assignations (executes_work), may not originate roots.
    - ``CALLER``       — originates root assignations (can_assign_root), does not execute.
    - ``ORCHESTRATOR`` — both executes work and originates roots.
    - ``OBSERVER``     — neither; a read-only dashboard that only streams events.
    """

    EXECUTOR = "EXECUTOR"
    CALLER = "CALLER"
    ORCHESTRATOR = "ORCHESTRATOR"
    OBSERVER = "OBSERVER"


class ToAgentMessageType(str, Enum):
    """The message types that can be sent to the agent from the rekuest backend"""

    ASSIGN = "ASSIGN"
    CANCEL = "CANCEL"
    STEP = "STEP"
    COLLECT = "COLLECT"
    RESUME = "RESUME"
    PAUSE = "PAUSE"
    INTERRUPT = "INTERRUPT"
    PROVIDE = "PROVIDE"
    UNPROVIDE = "UNPROVIDE"
    INIT = "INIT"
    HEARTBEAT = "HEARTBEAT"
    BOUNCE = "BOUNCE"
    KICK = "KICK"
    PROTOCOL_ERROR = "PROTOCOL_ERROR"
    EVENT_ACK = "EVENT_ACK"
    CALLER_ASSIGN_RESULT = "CALLER_ASSIGN_RESULT"
    # Caller-bound event mirrors — one per AssignationEventKind — streamed back to the
    # participant that originated the assignation (see ``CallerEvent`` and subclasses).
    CALLER_BOUND = "CALLER_BOUND"
    CALLER_QUEUED = "CALLER_QUEUED"
    CALLER_ASSIGNED = "CALLER_ASSIGNED"
    CALLER_PROGRESS = "CALLER_PROGRESS"
    CALLER_DELEGATE = "CALLER_DELEGATE"
    CALLER_DISCONNECTED = "CALLER_DISCONNECTED"
    CALLER_YIELD = "CALLER_YIELD"
    CALLER_DONE = "CALLER_DONE"
    CALLER_LOG = "CALLER_LOG"
    CALLER_CANCELING = "CALLER_CANCELING"
    CALLER_CANCELLED = "CALLER_CANCELLED"
    CALLER_INTERRUPTING = "CALLER_INTERRUPTING"
    CALLER_INTERRUPTED = "CALLER_INTERRUPTED"
    CALLER_ERROR = "CALLER_ERROR"
    CALLER_CRITICAL = "CALLER_CRITICAL"


class FromAgentMessageType(str, Enum):
    """The message types that can be sent from the agent to the rekuest backend"""

    REGISTER = "REGISTER"
    LOG = "LOG"
    PROGRESS = "PROGRESS"
    DONE = "DONE"
    YIELD = "YIELD"
    ERROR = "ERROR"
    PAUSED = "PAUSED"
    CRITICAL = "CRITICAL"
    STEPPED = "STEPPED"
    RESUMED = "RESUMED"
    CANCELLED = "CANCELLED"
    APP_CANCELLED = "APP_CANCELLED"  # Cancelled by the app not the user how assigned
    ASSIGNED = "ASSIGNED"
    INTERRUPTED = "INTERRUPTED"
    HEARTBEAT_ANSWER = "HEARTBEAT_ANSWER"
    STATE_PATCH = "STATE_PATCH"
    LOCK = "LOCK"
    UNLOCK = "UNLOCK"
    STATE_SNAPSHOT = "STATE_SNAPSHOT"
    SESSION_INIT = "SESSION_INIT"
    CALLER_ASSIGN = "CALLER_ASSIGN"


class Message(BaseModel):
    """A base message class"""

    # This is the local mapping of the message, reply messages should have the same id
    model_config = ConfigDict(use_enum_values=True, frozen=True)
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))


class FromAgentEvent(Message):
    """Base for agent→backend reporting events that participate in the ack/resume stream.

    ``seq`` is a monotonic, per-connection stream sequence used only for at-least-once
    **stream** dedup/resume — it is NOT an execution resume cursor (resuming execution
    from a position would require a recorded-effect log, which is deliberately out of
    scope). The backend dedups terminal reports by assignation id regardless of ``seq``.
    """

    seq: Optional[int] = Field(
        default=None,
        description="Monotonic per-connection stream sequence for at-least-once dedup/resume. Stream-level only — never an execution resume cursor.",
    )


class Assign(Message):
    """An assign call

    And assign call is the initial request to start a specific
    functionality and will have an assignation id, that will stand
    as a reference for all sub calls (Pause, Interrupt, Reumse, Collect...).
    as well should be passed to all events within the assignation (
        Progress, Logs, Done, Error, etc)
    )
    """

    type: Literal[ToAgentMessageType.ASSIGN] = ToAgentMessageType.ASSIGN
    interface: str = Field(description="The registered interface, that the agent should use to run this assignation")
    step: bool | None = Field(default=None, description="Whether to step the assignation or not (i.e. stop at the first breakpoint and wait for a step message from the rekuest backend to continue). If None don't step.")
    assignation: str = Field(description="The assignation id")
    root: Optional[str] = Field(
        default=None,
        description="The root of all cascaded assignations (user triggered assignation), None if this is the mother",
    )
    """ The mother assignation (root)"""
    parent: Optional[str] = Field(
        default=None,
        description="The direct parent of this assignation, None if this is this is the mother",
    )
    """ The parent s"""
    resolution: Optional[str] = Field(default=None, description="The resolution id this assignation has dependencies")
    capture: bool = Field(default=False, description="Whether to run in debug mode")
    reference: Optional[str] = Field(default=None, description="A reference that the assinger provided")
    args: Dict[str, ShallowJSONSerializable] = Field(description="The arguments that was sendend")
    message: Optional[str] = None
    user: str = Field(..., description="The assinging user")
    org: Optional[str] = Field(default=None, description="The org that the user currently belongs to")
    app: str = Field(description="The assinging app")
    action: str = Field(description="The action that triggered this assignation.")
    token: Optional[str] = Field(
        default=None,
        description="An opaque, signed provenance token attesting who caused this assignation and with which inputs. The agent forwards it untouched to downstream services; it does not validate it. None when the implementation opts out of provenance (needs_token=False).",
    )

    @property
    def actor_id(self) -> str:
        """The actor id is the id of the actor that will be used to run this assignation"""
        return self.interface


class Step(Message):
    """A step call
    A step call tells the agent to step the assignation
    and all its children assignation until a resume is received
    Its on the actor to decide what to do with the children assignations
    """

    type: Literal[ToAgentMessageType.STEP] = ToAgentMessageType.STEP
    assignation: str


class Bounce(Message):
    """A step call
    A step call tells the agent to step the assignation
    and all its children assignation until a resume is received
    Its on the actor to decide what to do with the children assignations
    """

    type: Literal[ToAgentMessageType.BOUNCE] = ToAgentMessageType.BOUNCE
    duration: int | None = None


class Kick(Message):
    """A step call
    A step call tells the agent to step the assignation
    and all its children assignation until a resume is received
    Its on the actor to decide what to do with the children assignations
    """

    type: Literal[ToAgentMessageType.KICK] = ToAgentMessageType.KICK
    reason: str | None = None


class Heartbeat(Message):
    """A heartbeat call
    A heartbeat call tells the agent to send a heartbeat
    and all its children assignation until a resume is received
    Its on the actor to decide what to do with the children assignations
    """

    type: Literal[ToAgentMessageType.HEARTBEAT] = ToAgentMessageType.HEARTBEAT


class Pause(Message):
    """A pause call

    A pause call tells the agent to pause the assignation
    and all its children assignation until a resume is received

    Its on the actor to decide what to do with the children assignations
    (i.e. pause them, cancel them, etc) or to raise an error if the
    state of the assignaiton wouldn't allow this.

    """

    type: Literal[ToAgentMessageType.PAUSE] = ToAgentMessageType.PAUSE
    assignation: str


class Resume(Message):
    """A resume call

    A resume call unpauses the pause"""

    type: Literal[ToAgentMessageType.RESUME] = ToAgentMessageType.RESUME
    assignation: str


class Cancel(Message):
    """A cancel call

    A cancellation call is a request from the user to
    cancel an assignation nicely (i.e by also nicely
    cancelling all the children assignations).
    Cancel represent a "nice alternative" to the interrupt call.
    While a cancellation of a mother task is only send to
    the mother to kill the children nicely (what the fuck is
    this metaphor), a interrupt will be send to all children
    automatically without the mother.


    Find more information on this in the arkitekt.live
    """

    type: Literal[ToAgentMessageType.CANCEL] = ToAgentMessageType.CANCEL
    assignation: str


class Collect(Message):
    """A collect call

    A collect call tells the agent to collect data LOCALLY,
    by deleting data on the "shelves" that live in memory.

    Find more information on this in the arkitekt.live
    documentation on local workflwos


    """

    type: Literal[ToAgentMessageType.COLLECT] = ToAgentMessageType.COLLECT
    drawers: list[str]


class Interrupt(Message):
    """A interrupt"""

    type: Literal[ToAgentMessageType.INTERRUPT] = ToAgentMessageType.INTERRUPT
    assignation: str


class CancelledEvent(FromAgentEvent):
    """A cancelled event"""

    type: Literal[FromAgentMessageType.CANCELLED] = FromAgentMessageType.CANCELLED
    assignation: str


class InterruptedEvent(FromAgentEvent):
    """An interrupted event

    A interruppted event is sent when the assignation was
    successfully interrupted by the actor.


    """

    type: Literal[FromAgentMessageType.INTERRUPTED] = FromAgentMessageType.INTERRUPTED
    assignation: str


class PausedEvent(FromAgentEvent):
    """A paused event

    A paused event is sent when the assignation was
    successfully paused by the actor.


    """

    type: Literal[FromAgentMessageType.PAUSED] = FromAgentMessageType.PAUSED
    assignation: str


class ResumedEvent(FromAgentEvent):
    """A resumed event

    A resumed event is sent when the assignation was
    successfully resumed by the actor.


    """

    type: Literal[FromAgentMessageType.RESUMED] = FromAgentMessageType.RESUMED
    assignation: str


class SteppedEvent(FromAgentEvent):
    """A stepped event

    A stepped event is sent when the assignation was
    successfully stepped by the actor and it has now
    stopped at another breakpoint.


    """

    type: Literal[FromAgentMessageType.STEPPED] = FromAgentMessageType.STEPPED


class LogEvent(FromAgentEvent):
    """A log event

    A log event is sent when the agent wants to send a log
    message to the rekuest backend. This is used to
    send logs from the agent to the rekuest backend
    """

    type: Literal[FromAgentMessageType.LOG] = FromAgentMessageType.LOG
    assignation: str
    message: str
    level: LogLevelLiteral = "INFO"
    """The log level of the message"""


class ProgressEvent(FromAgentEvent):
    """A progress event

    A progress event is sent when the agent wants to send a
    progress message to the rekuest backend. This is used to
    send progress from the agent to the rekuest backend
    """

    type: Literal[FromAgentMessageType.PROGRESS] = FromAgentMessageType.PROGRESS
    assignation: str
    progress: Optional[int] = None
    message: Optional[str] = None


class YieldEvent(FromAgentEvent):
    """A yield event

    A yield event is sent when the agent wants to send a
    yielded assignmented message to the rekuest backend. This is used to
    send yield from the agent to the rekuest backend
    """

    type: Literal[FromAgentMessageType.YIELD] = FromAgentMessageType.YIELD
    assignation: str
    returns: Optional[Dict[str, Any]] = None


class DoneEvent(FromAgentEvent):
    """A done event

    A done event is sent when the actor has finished the assignation
    and all its children assignation. This is used to
    send done from the agent to the rekuest backend
    """

    type: Literal[FromAgentMessageType.DONE] = FromAgentMessageType.DONE
    assignation: str


class ErrorEvent(FromAgentEvent):
    """An error event

    An error event is sent when the agent wants to send an error
    message to the rekuest backend. This is used to
    send errors from the agent to the rekuest backend.

    Errors are potentially recoverable, while critical errors are not.
    """

    type: Literal[FromAgentMessageType.ERROR] = FromAgentMessageType.ERROR
    assignation: str
    error: str


class CriticalEvent(FromAgentEvent):
    """A critical event

    A critical event is sent when the agent wants to send a critical
    message to the rekuest backend. This is used to
    send critical errors from the agent to the rekuest backend
    """

    type: Literal[FromAgentMessageType.CRITICAL] = FromAgentMessageType.CRITICAL
    assignation: str
    error: str


class HeartbeatEvent(Message):
    """A heartbeat event

    A heartbeat event is sent when the agent replies to a heartbeat
    message from the rekuest backend. Agents should never send
    heartbeat events, but only reply to them.
    """

    type: Literal[FromAgentMessageType.HEARTBEAT_ANSWER] = FromAgentMessageType.HEARTBEAT_ANSWER


class SessionInitMessage(Message):
    """A session init message

    A session init message is sent when the agent starts and wants to
    initialize the session with the rekuest backend. This is used to
    send session initialization information from the agent to the rekuest backend
    """

    type: Literal[FromAgentMessageType.SESSION_INIT] = FromAgentMessageType.SESSION_INIT
    session_id: str = Field(description="The session id of the agent (generated on a restart of the agent)")
    states: Dict[str, Any] = Field(description="A dictionary containing the initial state snapshots, where the key is the state name and the value is the state snapshot")


class StatePatchEvent(Message):
    """A state patch event

    A state patch event is sent when the agent wants to send a state patch
    to the rekuest backend. This is used to
    send state patches from the agent to the rekuest backend
    """

    type: Literal[FromAgentMessageType.STATE_PATCH] = FromAgentMessageType.STATE_PATCH
    session_id: str = Field(description="The session id of the agent (generated on a restart of the agent)")
    global_rev: int = Field(description="The global revision of the state")
    state_name: str = Field(description="The name of the state that is being patched")
    ts: float
    op: str
    path: str
    value: Any
    old_value: Any | None = Field(description="The old value of the patch, which can be used for debugging and tracing purposes")
    correlation_id: Optional[str] = Field(
        default=None,
        description="An optional correlation id to correlate this patch with a specific action or event in the agent's execution, which can be used for debugging and tracing purposes",
    )


class StateSnapshotEvent(Message):
    """A state snapshot event

    A state snapshot event is sent when the agent wants to send a state snapshot
    to the rekuest backend. This is used to
    send state patches from the agent to the rekuest backend
    """

    type: Literal[FromAgentMessageType.STATE_SNAPSHOT] = FromAgentMessageType.STATE_SNAPSHOT
    session_id: str = Field(description="The session id of the agent (generated on a restart of the agent)")
    global_rev: int = Field(description="The global revision of the state")
    snapshots: Dict[str, Any] = Field(description="A dictionary containing the state snapshots, where the key is the state name and the value is the state snapshot")


class LockEvent(Message):
    """A state patch event

    A state patch event is sent when the agent wants to send a state patch
    to the rekuest backend. This is used to
    send state patches from the agent to the rekuest backend
    """

    type: Literal[FromAgentMessageType.LOCK] = FromAgentMessageType.LOCK
    key: str
    assignation: str


class UnlockEvent(Message):
    """A state patch event

    A state patch event is sent when the agent wants to send a state patch
    to the rekuest backend. This is used to
    send state patches from the agent to the rekuest backend
    """

    type: Literal[FromAgentMessageType.UNLOCK] = FromAgentMessageType.UNLOCK
    key: str


class AssignInquiry(BaseModel):
    """An assign inquiry

    An assign inquiry is a request from rekuest_backend to the agent
    to check the state of a specific assignation. This is used to check if the
    assignation is still running or if after a reconnect has died.
    """

    assignation: str


class Register(Message):
    """A register message

    A register message is sent from the agent to the rekuest backend
    to register the agent with the rekuest backend. This is used to
    register the agent with the rekuest backend and to send the
    agent's token to the rekuest backend.

    """

    type: Literal[FromAgentMessageType.REGISTER] = FromAgentMessageType.REGISTER
    token: str
    force: bool = False
    """If another connection is already registered for this agent, kick it and take over.

    Only honoured for participants that ``executes_work`` (the executor singleton). A
    non-executor (frontend/observer) never force-displaces — its other connections coexist."""
    mode: AgentMode = Field(
        default=AgentMode.EXECUTOR,
        description="How this participant intends to use the protocol. Granted only if the token carries the matching capability scopes; otherwise the connection is closed with MODE_NOT_AUTHORIZED_CODE.",
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Per-process identifier minted in-memory by the executor at start-up (never persisted). Its volatility is the reclaim signal: a reconnect with the SAME session_id means the process survived (reclaim in-flight work); a DIFFERENT session_id means a fresh process (fail-and-cascade). Omitted by non-executors.",
    )


class ProtocolError(Message):
    type: Literal[ToAgentMessageType.PROTOCOL_ERROR] = ToAgentMessageType.PROTOCOL_ERROR
    error: str
    """ The error message that was raised by the agent"""


class Init(Message):
    """An init message

    An init message is sent from the rekuest backend to the agent
    as a response to the register message. It contains the
    information about the agent and the rekuest backend.
    """

    type: Literal[ToAgentMessageType.INIT] = ToAgentMessageType.INIT
    agent: str
    inquiries: list[AssignInquiry] = []


class CallerAssign(Message):
    """A caller's request to originate (or resolve) an assignation over the agent socket.

    This is the WebSocket equivalent of the GraphQL ``assign`` mutation: a participant
    holding ``can_assign_root`` (for a parentless root) or running inside a resolved
    assignation (for a dependent) asks the backend to create work and dispatch it to an
    executing agent. The fields mirror ``facade.inputs.AssignInputModel``.

    Creation safety is by **idempotency, not transport**: ``reference`` must be stable for
    a logical request, so a resend after reconnect returns the same assignation (see
    ``CallerAssignResult``) rather than creating a duplicate.
    """

    type: Literal[FromAgentMessageType.CALLER_ASSIGN] = FromAgentMessageType.CALLER_ASSIGN
    reference: str = Field(description="Caller-supplied idempotency key. Stable across resends of the same logical request.")
    args: Dict[str, ShallowJSONSerializable] = Field(default_factory=dict, description="The args of the assignation (ports → values).")
    action: Optional[str] = Field(default=None, description="The action ID to assign to.")
    action_hash: Optional[str] = Field(default=None, description="The action hash to assign to.")
    implementation: Optional[str] = Field(default=None, description="A direct implementation ID to assign to.")
    agent: Optional[str] = Field(default=None, description="A direct agent ID to assign to (with interface).")
    interface: Optional[str] = Field(default=None, description="The implementation interface (only with agent).")
    parent: Optional[str] = Field(default=None, description="The parent assignation ID. None for a root assignation (requires can_assign_root).")
    dependency: Optional[str] = Field(default=None, description="The dependency key to resolve when running inside a resolved assignation.")
    method: Optional[str] = Field(default=None, description="The dependency method to assign.")
    resolution: Optional[str] = Field(default=None, description="The resolution ID for an implementation with dependencies.")
    hooks: Optional[List[Dict[str, Any]]] = Field(default=None, description="Lifecycle hooks for the assignation.")
    capture: Optional[bool] = Field(default=None, description="Whether to run in debug capture mode.")
    ephemeral: Optional[bool] = Field(default=None, description="Whether the assignation is ephemeral.")
    step: Optional[bool] = Field(default=None, description="Whether to step to breakpoints.")


class CallerAssignResult(Message):
    """The backend's authoritative ack that a ``CallerAssign`` was persisted.

    Echoes the originating request id (``request``) and carries the durable assignation
    id, so the caller can map ``reference``/``request`` → ``assignation`` BEFORE any
    subsequent assignation events arrive (those are keyed only by assignation id). A
    resend of the same ``reference`` yields the same ``assignation`` with ``created=False``.
    """

    type: Literal[ToAgentMessageType.CALLER_ASSIGN_RESULT] = ToAgentMessageType.CALLER_ASSIGN_RESULT
    request: str = Field(description="The id of the CallerAssign this result answers.")
    reference: str = Field(description="The idempotency key echoed from the request.")
    assignation: Optional[str] = Field(default=None, description="The durable assignation id, or None when error is set.")
    created: bool = Field(default=True, description="False when an existing assignation was returned for a duplicate reference.")
    error: Optional[str] = Field(default=None, description="A human-readable error if the assign was rejected (e.g. missing can_assign_root).")


class EventAck(Message):
    """Backend → agent acknowledgement that a reported event was made durable.

    The agent retains terminal reports (done/error/critical/cancelled) until it receives
    the matching ``EventAck`` and resends them on reconnect; this ack (persist-then-ack)
    is what makes that retain-and-resend safe. Correlates by the acked event's id.
    """

    type: Literal[ToAgentMessageType.EVENT_ACK] = ToAgentMessageType.EVENT_ACK
    event: str = Field(description="The id of the FromAgentEvent being acknowledged.")
    assignation: Optional[str] = Field(default=None, description="The assignation the acked event belonged to, for convenience.")
    seq: Optional[int] = Field(default=None, description="The stream sequence acknowledged, if the event carried one.")


class CallerEvent(Message):
    """Base for backend→caller assignation-event mirrors.

    When a participant originates work (``CallerAssign``), each resulting assignation
    event is streamed back to it over its own socket as one of the ``Caller*`` subclasses
    below — a minimal mirror of the persisted ``AssignationEvent``, so the caller never
    needs GraphQL to read results. Delivery is best-effort (the ``ass_caller_{caller_id}``
    channel-layer group); on a brief disconnect events are missed and the caller
    re-inquires on reconnect.

    Correlation: ``assignation`` is the key the caller already learned from
    ``CallerAssignResult``. ``event`` is the originating ``AssignationEvent`` id (a stable
    dedup handle) and ``seq`` its monotonic PK (an ordering / gap-detection key).
    """

    assignation: str = Field(description="The assignation this event belongs to (the caller's correlation key).")
    event: str = Field(description="The originating AssignationEvent id — a stable dedup handle.")
    seq: int = Field(description="The originating AssignationEvent's monotonic PK — ordering / gap-detection key.")


class CallerBound(CallerEvent):
    """The assignation was bound to an agent."""

    type: Literal[ToAgentMessageType.CALLER_BOUND] = ToAgentMessageType.CALLER_BOUND


class CallerQueued(CallerEvent):
    """The assignation was queued."""

    type: Literal[ToAgentMessageType.CALLER_QUEUED] = ToAgentMessageType.CALLER_QUEUED


class CallerAssigned(CallerEvent):
    """The agent accepted the assignation."""

    type: Literal[ToAgentMessageType.CALLER_ASSIGNED] = ToAgentMessageType.CALLER_ASSIGNED


class CallerProgress(CallerEvent):
    """The executing agent reported progress."""

    type: Literal[ToAgentMessageType.CALLER_PROGRESS] = ToAgentMessageType.CALLER_PROGRESS
    progress: Optional[int] = None
    message: Optional[str] = None


class CallerDelegate(CallerEvent):
    """The assignation was delegated to another assignation."""

    type: Literal[ToAgentMessageType.CALLER_DELEGATE] = ToAgentMessageType.CALLER_DELEGATE


class CallerDisconnected(CallerEvent):
    """The executing agent disconnected; the assignation's fate is (for now) unknown."""

    type: Literal[ToAgentMessageType.CALLER_DISCONNECTED] = ToAgentMessageType.CALLER_DISCONNECTED
    message: Optional[str] = None


class CallerYield(CallerEvent):
    """The executing agent yielded a result."""

    type: Literal[ToAgentMessageType.CALLER_YIELD] = ToAgentMessageType.CALLER_YIELD
    returns: Optional[Dict[str, Any]] = None


class CallerDone(CallerEvent):
    """The assignation finished successfully."""

    type: Literal[ToAgentMessageType.CALLER_DONE] = ToAgentMessageType.CALLER_DONE


class CallerLog(CallerEvent):
    """A log line from the executing agent."""

    type: Literal[ToAgentMessageType.CALLER_LOG] = ToAgentMessageType.CALLER_LOG
    message: Optional[str] = None
    level: LogLevelLiteral = "INFO"


class CallerCanceling(CallerEvent):
    """The assignation is being cancelled."""

    type: Literal[ToAgentMessageType.CALLER_CANCELING] = ToAgentMessageType.CALLER_CANCELING


class CallerCancelled(CallerEvent):
    """The assignation was cancelled."""

    type: Literal[ToAgentMessageType.CALLER_CANCELLED] = ToAgentMessageType.CALLER_CANCELLED


class CallerInterrupting(CallerEvent):
    """The assignation is being interrupted."""

    type: Literal[ToAgentMessageType.CALLER_INTERRUPTING] = ToAgentMessageType.CALLER_INTERRUPTING


class CallerInterrupted(CallerEvent):
    """The assignation was interrupted."""

    type: Literal[ToAgentMessageType.CALLER_INTERRUPTED] = ToAgentMessageType.CALLER_INTERRUPTED


class CallerError(CallerEvent):
    """The assignation errored (potentially recoverable)."""

    type: Literal[ToAgentMessageType.CALLER_ERROR] = ToAgentMessageType.CALLER_ERROR
    error: Optional[str] = None


class CallerCritical(CallerEvent):
    """The assignation hit an unrecoverable error."""

    type: Literal[ToAgentMessageType.CALLER_CRITICAL] = ToAgentMessageType.CALLER_CRITICAL
    error: Optional[str] = None


# Every Caller* mirror, in AssignationEventKind order. Imported by ``facade.caller_events``.
CallerEventMessage = Union[
    CallerBound,
    CallerQueued,
    CallerAssigned,
    CallerProgress,
    CallerDelegate,
    CallerDisconnected,
    CallerYield,
    CallerDone,
    CallerLog,
    CallerCanceling,
    CallerCancelled,
    CallerInterrupting,
    CallerInterrupted,
    CallerError,
    CallerCritical,
]


ToAgentMessage = Union[
    Init,
    Assign,
    Cancel,
    Interrupt,
    Heartbeat,
    Step,
    Pause,
    Resume,
    Collect,
    ProtocolError,
    Bounce,
    Kick,
    EventAck,
    CallerAssignResult,
    CallerBound,
    CallerQueued,
    CallerAssigned,
    CallerProgress,
    CallerDelegate,
    CallerDisconnected,
    CallerYield,
    CallerDone,
    CallerLog,
    CallerCanceling,
    CallerCancelled,
    CallerInterrupting,
    CallerInterrupted,
    CallerError,
    CallerCritical,
]
FromAgentMessage = Union[CriticalEvent, LogEvent, ProgressEvent, DoneEvent, ErrorEvent, YieldEvent, Register, HeartbeatEvent, SteppedEvent, ResumedEvent, PausedEvent, CancelledEvent, InterruptedEvent, StatePatchEvent, StateSnapshotEvent, LockEvent, UnlockEvent, SessionInitMessage, CallerAssign]
