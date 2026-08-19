from .settings import *  # noqa
from .settings import DATABASES, AUTHENTIKATE, DATALAYER
import logging


# There is no STS to assume a role against under unit tests, and a grant that cannot be scoped
# now refuses rather than quietly returning this service's permanent key. Tests that exercise a
# grant care about its *shape*, not its credentials, so let them have the unscoped one.
DATALAYER = {**DATALAYER, "allow_unscoped_fallback": True}

DATABASES["default"] = {**DATABASES["default"], "NAME": "testdb", "PORT": 5555, "HOST": "localhost", "USER": "test", "PASSWORD": "test"}
AUTHENTIKATE = {
    **AUTHENTIKATE,
    "static_tokens": {
        "test": {"sub": "1", "client_id": "oinsoins", "app": "test-app"},
        # A second distinct identity (same default ``static_org``) for cross-agent tests —
        # agent 1 (token "test") assigns to agent 2 (token "test2").
        "test2": {"sub": "2", "client_id": "oinsoins2", "app": "test-app"},
    },
}


# For faster test execution, you can uncomment this:
# MIGRATION_MODULES = DisableMigrations()

# Disable logging during tests to reduce noise
logging.disable(logging.CRITICAL)

# Enable database access from async code in tests
DATABASE_ROUTERS = []

# Use in-memory channel layer for tests instead of Redis
CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}

# Default tests to grace=0 → disconnects cascade inline/immediately (the legacy,
# deterministic behavior). The reclaim/grace tests opt into a window with override_settings.
REKUEST_GRACE = {"DEFAULT": 0, "PHYSICAL": 0}

# Point the agent queue at the published dokker redis port (see
# tests/integration/docker-compose.yaml). Replaces the old redis-factory monkeypatch.
AGENT_REDIS_HOST = "localhost"
AGENT_REDIS_PORT = 6666

# Probes: short TTLs so expiry behavior is testable without waiting.
TASK_RETENTION_SECONDS = 0
PROBE_TTL_SECONDS = 60
PROBE_LINGER_SECONDS = 30
PROBE_MAX_INFLIGHT_PER_CALLER = 8
