"""auto_interrupt escalation + manual escalation, driving ``ModelPersistBackend`` directly
(a fresh instance isolates the in-memory timer registry, like the reclaim/grace tests).

A cancel that carries ``auto_interrupt=<seconds>`` escalates to an interrupt if the agent
hasn't confirmed within the window; a confirmed (or otherwise terminal) cancel cancels the
timer; ``None`` disables escalation entirely.
"""

import asyncio

import pytest

from facade import enums, messages
from facade.models import Assignation, AssignationEvent
from facade.persist_backend import ModelPersistBackend

from tests.factories import build_assignation_for_agent_caller, seed_agent

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.asyncio]


async def _owned(prefix):
    """A seeded agent + an assignation whose caller is that agent (so it may control it)."""
    agent = await seed_agent(f"{prefix}-agent")
    ass = await build_assignation_for_agent_caller(agent.pk, prefix)
    return agent, ass


async def _kinds(ass_id):
    return [e.kind async for e in AssignationEvent.objects.filter(assignation_id=ass_id)]


class TestAutoInterrupt:
    async def test_fires_and_escalates_to_interrupt(self):
        agent, ass = await _owned("ai-fire")
        backend = ModelPersistBackend()
        key = str(ass.pk)

        await backend.on_caller_cancel(agent.pk, messages.CallerCancel(assignation=key, auto_interrupt=0.05))
        assert key in backend._auto_interrupt  # CANCELING persisted, timer armed
        await asyncio.wait_for(backend._auto_interrupt[key], timeout=2)

        kinds = await _kinds(ass.pk)
        assert enums.AssignationEventKind.CANCELING in kinds
        assert enums.AssignationEventKind.INTERUPTING in kinds  # escalated

    async def test_none_disables_escalation(self):
        agent, ass = await _owned("ai-none")
        backend = ModelPersistBackend()
        await backend.on_caller_cancel(agent.pk, messages.CallerCancel(assignation=str(ass.pk)))
        assert str(ass.pk) not in backend._auto_interrupt

    async def test_confirm_before_window_cancels_timer(self):
        agent, ass = await _owned("ai-confirm")
        backend = ModelPersistBackend()
        key = str(ass.pk)

        await backend.on_caller_cancel(agent.pk, messages.CallerCancel(assignation=key, auto_interrupt=30))
        assert key in backend._auto_interrupt
        await backend.on_agent_cancelled(agent.pk, messages.CancelledEvent(assignation=key))
        assert key not in backend._auto_interrupt  # cancelled on terminal
        assert enums.AssignationEventKind.INTERUPTING not in await _kinds(ass.pk)

    async def test_escalation_is_noop_if_already_terminal(self):
        agent, ass = await _owned("ai-terminal")
        await Assignation.objects.filter(pk=ass.pk).aupdate(is_done=True)
        backend = ModelPersistBackend()

        await backend._escalate_to_interrupt(str(ass.pk))  # re-reads is_done → no-op

        assert enums.AssignationEventKind.INTERUPTING not in await _kinds(ass.pk)

    async def test_terminal_by_other_path_cancels_timer(self):
        agent, ass = await _owned("ai-other")
        backend = ModelPersistBackend()
        key = str(ass.pk)
        await backend.on_caller_cancel(agent.pk, messages.CallerCancel(assignation=key, auto_interrupt=30))
        await backend.on_agent_done(agent.pk, messages.DoneEvent(assignation=key))
        assert key not in backend._auto_interrupt


class TestManualEscalation:
    async def test_manual_cancel_then_interrupt(self):
        agent, ass = await _owned("me")
        backend = ModelPersistBackend()
        key = str(ass.pk)

        await backend.on_caller_cancel(agent.pk, messages.CallerCancel(assignation=key))  # CANCELING, not terminal
        await backend.on_caller_interrupt(agent.pk, messages.CallerInterrupt(assignation=key))  # INTERUPTING

        kinds = await _kinds(ass.pk)
        assert enums.AssignationEventKind.CANCELING in kinds and enums.AssignationEventKind.INTERUPTING in kinds

        await backend.on_agent_interrupted(agent.pk, messages.InterruptedEvent(assignation=key))
        refreshed = await Assignation.objects.aget(pk=ass.pk)
        assert refreshed.is_done is True and refreshed.latest_event_kind == enums.AssignationEventKind.INTERUPTED
