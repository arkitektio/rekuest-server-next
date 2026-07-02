"""The replay primitive: Task.args_hash + the reusable_task_for discovery query.

Replay/reuse of prior results is the ORCHESTRATOR's decision — the server never
short-circuits an assign. It only (a) stamps every task with the canonical args hash at
assign time and (b) surfaces the latest completed run of a PURE action for identical args
via ``reusable_task_for``. Non-pure actions are never offered for replay.
"""

from types import SimpleNamespace

import pytest
from django.utils import timezone

from facade import enums, inputs, models
from facade.backend import controll_backend
from facade.caller_context import CallerContext
from facade.provenance.canonical import args_hash
from facade.queries.task import reusable_task_for

from tests.factories import _build_implementation_for_agent, _build_webhook_agent

pytestmark = pytest.mark.django_db


@pytest.fixture
def broadcasts(monkeypatch):
    from facade.consumers.async_consumer import AgentConsumer

    recorded = []
    monkeypatch.setattr(AgentConsumer, "broadcast", staticmethod(lambda agent_id, message: recorded.append((agent_id, message))))
    return recorded


@pytest.fixture
def setup(broadcasts):
    agent = _build_webhook_agent("replay")
    implementation = _build_implementation_for_agent(agent.pk, "replay")
    models.Action.objects.filter(pk=implementation.action_id).update(pure=True, idempotent=True)
    implementation.action.refresh_from_db()
    ctx = CallerContext.from_agent(agent)
    return SimpleNamespace(agent=agent, implementation=implementation, action=implementation.action, ctx=ctx)


def _assign(setup, args):
    return controll_backend.assign(setup.ctx, inputs.AssignInputModel(action=str(setup.action.pk), args=args))


def _complete(task, returns):
    models.TaskEvent.objects.create(task=task, kind=enums.TaskEventKind.YIELD, returns=returns)
    models.TaskEvent.objects.create(task=task, kind=enums.TaskEventKind.COMPLETED)
    task.is_done = True
    task.finished_at = timezone.now()
    task.latest_event_kind = enums.TaskEventKind.COMPLETED
    task.save(update_fields=["is_done", "finished_at", "latest_event_kind"])


def _info(organization):
    return SimpleNamespace(context=SimpleNamespace(request=SimpleNamespace(organization=organization)))


def test_assign_stamps_canonical_args_hash(setup):
    first = _assign(setup, {"b": 2, "a": 1})
    second = _assign(setup, {"a": 1, "b": 2})
    third = _assign(setup, {"a": 1, "b": 3})

    assert first.args_hash == args_hash({"a": 1, "b": 2})
    assert first.args_hash == second.args_hash  # key order is canonicalized away
    assert first.args_hash != third.args_hash


def test_reusable_task_for_offers_completed_pure_run(setup):
    task = _assign(setup, {"a": 1})
    info = _info(setup.agent.organization)

    # Still running → nothing to reuse.
    assert reusable_task_for(info, setup.action.hash, {"a": 1}) is None

    _complete(task, {"out": 42})

    hit = reusable_task_for(info, setup.action.hash, {"a": 1})
    assert hit is not None
    assert hit.pk == task.pk
    # The orchestrator reads the returns off the REAL prior task's YIELD events.
    assert hit.events.get(kind=enums.TaskEventKind.YIELD).returns == {"out": 42}

    # Different args → no offer.
    assert reusable_task_for(info, setup.action.hash, {"a": 2}) is None


def test_non_pure_actions_are_never_offered(setup):
    task = _assign(setup, {"a": 1})
    _complete(task, {"out": 42})
    models.Action.objects.filter(pk=setup.action.pk).update(pure=False)

    assert reusable_task_for(_info(setup.agent.organization), setup.action.hash, {"a": 1}) is None


def test_ephemeral_runs_are_never_offered(setup):
    task = _assign(setup, {"a": 1})
    _complete(task, {"out": 42})
    models.Task.objects.filter(pk=task.pk).update(ephemeral=True)

    assert reusable_task_for(_info(setup.agent.organization), setup.action.hash, {"a": 1}) is None


def test_replay_is_organization_scoped(setup):
    from authentikate.models import Organization

    task = _assign(setup, {"a": 1})
    _complete(task, {"out": 42})

    other_org = Organization.objects.create(slug="replay-other-org")
    assert reusable_task_for(_info(other_org), setup.action.hash, {"a": 1}) is None


def test_latest_completed_run_wins(setup):
    older = _assign(setup, {"a": 1})
    _complete(older, {"out": 1})
    newer = _assign(setup, {"a": 1})
    _complete(newer, {"out": 2})

    hit = reusable_task_for(_info(setup.agent.organization), setup.action.hash, {"a": 1})
    assert hit.pk == newer.pk
