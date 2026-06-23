"""HookAgents — the agent protocol over HTTP POST.

Covers the signing helper, outbound delivery branching (broadcast → POST for WEBHOOK),
the caller-event callback, and the HTTP intake (HMAC-verified, routed through the shared
dispatcher). httpx is stubbed so no real network calls happen.
"""

import json

import pytest
from django.test import RequestFactory

from facade import enums, hooks, messages
from facade.consumers.async_consumer import AgentConsumer
from facade.http_intake import hook_intake
from facade.models import Task, TaskEvent

from tests.factories import (
    _build_task,
    _build_webhook_agent,
    build_task,
    build_implementation_for_agent,
    build_webhook_agent,
)


class _FakeResp:
    status_code = 200

    def raise_for_status(self):
        return None


class _Recorder:
    """Captures outbound POSTs in place of httpx."""

    def __init__(self):
        self.calls = []

    def __call__(self, url, content=None, headers=None):
        self.calls.append({"url": url, "content": content, "headers": headers or {}})
        return _FakeResp()


@pytest.fixture
def post_recorder(monkeypatch):
    rec = _Recorder()
    monkeypatch.setattr(hooks._client, "post", rec)
    return rec


# --------------------------------------------------------------------------- #
# Signing
# --------------------------------------------------------------------------- #
def test_sign_verify_roundtrip_and_tamper():
    body = b'{"hello": 1}'
    sig = hooks.sign("secret", body)
    assert hooks.verify("secret", body, sig) is True
    assert hooks.verify("secret", b'{"hello": 2}', sig) is False  # body tampered
    assert hooks.verify("wrong", body, sig) is False  # wrong secret
    assert hooks.verify("secret", body, None) is False
    assert hooks.verify(None, body, sig) is False


# --------------------------------------------------------------------------- #
# Outbound delivery branch
# --------------------------------------------------------------------------- #
@pytest.mark.django_db(transaction=True)
def test_broadcast_to_webhook_posts_signed(post_recorder):
    agent = _build_webhook_agent("hook-out", secret="topsecret", hook_url="https://hook.example/in")
    AgentConsumer.broadcast(str(agent.pk), messages.Cancel(task="ass-1"))

    assert len(post_recorder.calls) == 1
    call = post_recorder.calls[0]
    assert call["url"] == "https://hook.example/in"
    body = call["content"]
    assert json.loads(body)["type"] == messages.ToAgentMessageType.CANCEL.value
    # Signed with the agent's secret.
    assert call["headers"][hooks.SIGNATURE_HEADER] == hooks.sign("topsecret", body)


# --------------------------------------------------------------------------- #
# Caller-event callback (signal → POST)
# --------------------------------------------------------------------------- #
@pytest.mark.django_db(transaction=True)
def test_caller_event_is_posted_to_webhook_caller(post_recorder):
    from facade.models import Caller

    agent = _build_webhook_agent("hook-cb")
    # An task whose caller is this webhook agent's identity.
    caller = Caller.objects.create(client=agent.client, user=agent.user, organization=agent.organization)
    ass = _build_task("hook-cb-ass")
    ass.caller = caller
    ass.save(update_fields=["caller"])

    TaskEvent.objects.create(task=ass, kind=enums.TaskEventKind.PROGRESS, progress=42)

    assert any(json.loads(c["content"]).get("type") == messages.ToAgentMessageType.PROGRESS_EVENT.value for c in post_recorder.calls)


# --------------------------------------------------------------------------- #
# HTTP intake
# --------------------------------------------------------------------------- #
def _signed_request(agent, message):
    body = message.model_dump_json().encode("utf-8")
    sig = hooks.sign(agent.hook_url_secret, body)
    return RequestFactory().post(
        f"/agi/http/{agent.pk}", data=body, content_type="application/json",
        **{f"HTTP_{hooks.SIGNATURE_HEADER.upper().replace('-', '_')}": sig},
    )


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestHookIntake:
    async def test_caller_assign_over_http(self, post_recorder):
        agent = await build_webhook_agent("hook-in-ca", secret="sek")
        impl = await build_implementation_for_agent(agent.pk, "hook-in-ca")

        msg = messages.AssignRequest(reference="hr-1", implementation=str(impl.pk), args={"x": 1})
        response = await hook_intake(_signed_request(agent, msg), str(agent.pk))

        assert response.status_code == 200
        data = json.loads(response.content)
        assert data["type"] == messages.ToAgentMessageType.ASSIGN_RESPONSE.value
        assert data["reference"] == "hr-1" and data["created"] is True and data["task"]
        assert await Task.objects.filter(reference="hr-1").acount() == 1

    async def test_bad_signature_is_rejected(self, post_recorder):
        agent = await build_webhook_agent("hook-in-bad", secret="sek")
        body = messages.Completed(task="x").model_dump_json().encode("utf-8")
        request = RequestFactory().post(
            f"/agi/http/{agent.pk}", data=body, content_type="application/json",
            **{f"HTTP_{hooks.SIGNATURE_HEADER.upper().replace('-', '_')}": "deadbeef"},
        )
        response = await hook_intake(request, str(agent.pk))
        assert response.status_code == 401

    async def test_done_event_over_http_acks_and_persists(self, post_recorder):
        agent = await build_webhook_agent("hook-in-done", secret="sek")
        ass = await build_task("hook-in-done-ass")

        msg = messages.Completed(task=str(ass.pk), seq=3)
        response = await hook_intake(_signed_request(agent, msg), str(agent.pk))

        assert response.status_code == 200
        data = json.loads(response.content)
        assert data["type"] == messages.ToAgentMessageType.EVENT_ACK.value
        assert data["event"] == msg.id
        refreshed = await Task.objects.aget(pk=ass.pk)
        assert refreshed.is_done is True


# --------------------------------------------------------------------------- #
# Connectivity — a webhook agent is selectable despite connected=False
# --------------------------------------------------------------------------- #
@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_action_assign_selects_webhook_agent(post_recorder):
    from asgiref.sync import sync_to_async

    from facade.backend import controll_backend, agent_is_available
    from facade.caller_context import CallerContext
    from facade import inputs

    agent = await build_webhook_agent("hook-action", secret="sek")
    impl = await build_implementation_for_agent(agent.pk, "hook-action")

    assert agent_is_available(agent) is True  # webhook agent, despite connected=False

    ctx = CallerContext.from_agent(agent)
    action_id = str(impl.action_id)
    task = await sync_to_async(controll_backend.assign)(
        ctx, inputs.AssignInputModel(action=action_id, args={})
    )
    assert str(task.agent_id) == str(agent.pk)
