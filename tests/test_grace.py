"""Unit tests for the per-mode reclaim grace-window accessor."""

from django.test import override_settings

from facade.grace import grace_seconds
from facade.messages import AgentMode


@override_settings(REKUEST_GRACE={"DEFAULT": 30, "PER_MODE": {"OBSERVER": 0}, "PHYSICAL": 5})
def test_default_per_mode_and_physical_resolution():
    assert grace_seconds(AgentMode.EXECUTOR) == 30  # falls back to DEFAULT
    assert grace_seconds(AgentMode.OBSERVER) == 0  # per-mode override
    assert grace_seconds(AgentMode.EXECUTOR, physical=True) == 5  # physical override wins
    assert grace_seconds() == 30  # no mode -> DEFAULT
    assert grace_seconds("CALLER") == 30  # accepts the raw string value too


@override_settings(REKUEST_GRACE={"DEFAULT": 0})
def test_strict_zero_grace():
    assert grace_seconds(AgentMode.EXECUTOR) == 0
    # No PHYSICAL configured -> physical falls through to DEFAULT.
    assert grace_seconds(AgentMode.EXECUTOR, physical=True) == 0
