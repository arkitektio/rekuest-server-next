"""Unit tests for the unified liveness window (``facade.liveness``).

Pure predicate + Q-builder tests: no Channels, no redis. The Q tests hit the DB (agent rows)
and so are marked ``django_db``.
"""

import datetime

import pytest
from django.utils import timezone

from facade import enums, liveness, models
from tests.factories import create_agent_for_registry, create_registry_bundle


def _stale() -> float:
    return liveness.stale_after_seconds()


class TestAgentIsLive:
    def test_disconnected_is_not_live(self):
        assert liveness.agent_is_live(False, timezone.now()) is False

    def test_connected_without_last_seen_is_not_live(self):
        assert liveness.agent_is_live(True, None) is False

    def test_connected_and_fresh_is_live(self):
        assert liveness.agent_is_live(True, timezone.now()) is True

    def test_just_inside_window_is_live(self):
        last_seen = timezone.now() - datetime.timedelta(seconds=_stale() - 2)
        assert liveness.agent_is_live(True, last_seen) is True

    def test_just_outside_window_is_stale(self):
        last_seen = timezone.now() - datetime.timedelta(seconds=_stale() + 2)
        assert liveness.agent_is_live(True, last_seen) is False


@pytest.mark.django_db
class TestLivenessQueries:
    def _agent(self, prefix, connected, last_seen, kind=enums.AgentKind.WEBSOCKET.value):
        # Full identity graph (unique per client/user/org); liveness Qs read connected/last_seen/kind.
        user, client, org, caller = create_registry_bundle(prefix)
        return create_agent_for_registry(caller, user, org, prefix, connected=connected, last_seen=last_seen, kind=kind)

    def test_live_and_stale_qs_partition_connected_agents(self):
        fresh = self._agent("fresh", True, timezone.now())
        stale = self._agent("stale", True, timezone.now() - datetime.timedelta(seconds=_stale() + 5))
        never = self._agent("never", True, None)
        disconnected = self._agent("disc", False, timezone.now() - datetime.timedelta(seconds=_stale() + 5))

        live_ids = set(models.Agent.objects.filter(liveness.live_agent_q(prefix="")).values_list("id", flat=True))
        stale_ids = set(models.Agent.objects.filter(liveness.stale_agent_q(prefix="")).values_list("id", flat=True))

        assert live_ids == {fresh.id}
        # stuck-connected (expired OR never-seen), but never a disconnected row
        assert stale_ids == {stale.id, never.id}
        assert disconnected.id not in live_ids and disconnected.id not in stale_ids
