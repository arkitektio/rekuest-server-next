"""GraphQL enums and Django ``TextChoices`` for the facade app.

Split into domain submodules. This ``__init__`` re-exports every public enum so
the established ``from facade import enums`` / ``enums.X`` access keeps working.
"""

from .action import ActionKindChoices, ActionScope, DemandKind, EffectClassChoices, HookKind
from .agent import (
    AgentEventChoices,
    AgentEventKind,
    AgentKind,
    AgentStatus,
)
from rekuest_core.enums import AssignPolicy
from .task import (
    TaskEventChoices,
    TaskEventKind,
    TaskInstructChoices,
    TaskInstructKind,
    TaskStatus,
)
from .log import LogLevel, LogLevelChoices
from .state import JSONPatchOperation, RetentionPolicyChoices

__all__ = [
    # action
    "ActionKindChoices",
    "ActionScope",
    "DemandKind",
    "EffectClassChoices",
    "HookKind",
    # agent
    "AgentEventChoices",
    "AgentEventKind",
    "AgentKind",
    "AgentStatus",
    # task
    "TaskEventChoices",
    "TaskEventKind",
    "TaskInstructChoices",
    "TaskInstructKind",
    "TaskStatus",
    "AssignPolicy",
    # log
    "LogLevel",
    "LogLevelChoices",
    # state
    "JSONPatchOperation",
    "RetentionPolicyChoices",
]
