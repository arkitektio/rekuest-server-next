"""Capability resolution for the single agent protocol.

Every participant — executor subagent, frontend, dashboard — speaks the *same* agent
protocol; what differs is **capability**, resolved from the token's OAuth scopes and
**never self-declared**. There are two independent axes:

- ``executes_work``   — runs assignations. Its connection is the executor *singleton*
  (one live, force-displaces) and its disconnect drives the failure cascade.
- ``can_assign_root`` — may originate *root* (parentless) assignations.

The four ``AgentMode`` values are the four combinations (see :class:`messages.AgentMode`).
A requested mode is only granted if the token carries the capabilities it requires.

Rollout safety: enforcement is **opt-in** (``REKUEST_CAPABILITIES.ENFORCE``, default
False). While disabled, every authenticated participant resolves to a full
executor-and-caller — i.e. exactly today's behaviour — so existing agents whose tokens
predate these scopes keep working. Flip ``ENFORCE`` on once tokens carry the scopes.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings

from facade.messages import AgentMode

# Defaults — overridable per deployment via the ``REKUEST_CAPABILITIES`` setting so a
# deployment can remap them to whatever scope strings its ``lok`` issuer mints.
DEFAULT_EXECUTES_WORK_SCOPE = "rekuest:execute"
DEFAULT_CAN_ASSIGN_ROOT_SCOPE = "rekuest:assign_root"


@dataclass(frozen=True)
class Capabilities:
    """The capabilities granted to a connection, resolved from token scopes."""

    executes_work: bool
    can_assign_root: bool


def _conf() -> dict:
    return getattr(settings, "REKUEST_CAPABILITIES", {}) or {}


def _enforced() -> bool:
    return bool(_conf().get("ENFORCE", False))


def executes_work_scope() -> str:
    return _conf().get("EXECUTES_WORK_SCOPE", DEFAULT_EXECUTES_WORK_SCOPE)


def can_assign_root_scope() -> str:
    return _conf().get("CAN_ASSIGN_ROOT_SCOPE", DEFAULT_CAN_ASSIGN_ROOT_SCOPE)


def capabilities_from_scopes(scopes: list[str]) -> Capabilities:
    """Resolve granted capabilities from a token's scopes.

    When enforcement is off (the rollout default) every authenticated participant is a
    full executor-and-caller, preserving legacy behaviour. When on, capabilities are
    strictly the scopes present on the token.
    """
    if not _enforced():
        return Capabilities(executes_work=True, can_assign_root=True)

    scopes = scopes or []
    return Capabilities(
        executes_work=executes_work_scope() in scopes,
        can_assign_root=can_assign_root_scope() in scopes,
    )


def required_for_mode(mode: AgentMode) -> Capabilities:
    """The capabilities a mode *requires* to be granted."""
    return {
        AgentMode.EXECUTOR: Capabilities(executes_work=True, can_assign_root=False),
        AgentMode.CALLER: Capabilities(executes_work=False, can_assign_root=True),
        AgentMode.ORCHESTRATOR: Capabilities(executes_work=True, can_assign_root=True),
        AgentMode.OBSERVER: Capabilities(executes_work=False, can_assign_root=False),
    }[AgentMode(mode)]


def authorize_mode(granted: Capabilities, mode: AgentMode) -> bool:
    """True iff ``granted`` covers everything ``mode`` requires."""
    req = required_for_mode(mode)
    if req.executes_work and not granted.executes_work:
        return False
    if req.can_assign_root and not granted.can_assign_root:
        return False
    return True


def mode_executes_work(mode: AgentMode) -> bool:
    """Whether a connection in this mode is the executor singleton."""
    return AgentMode(mode) in (AgentMode.EXECUTOR, AgentMode.ORCHESTRATOR)


def mode_can_assign_root(mode: AgentMode) -> bool:
    """Whether a connection in this mode may originate root assignations."""
    return AgentMode(mode) in (AgentMode.CALLER, AgentMode.ORCHESTRATOR)
