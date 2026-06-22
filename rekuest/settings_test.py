from .settings import *  # noqa
from .settings import DATABASES, AUTHENTIKATE
import logging

DATABASES["default"] = {**DATABASES["default"], "NAME": "testdb", "PORT": 5555, "HOST": "localhost", "USER": "test", "PASSWORD": "test"}
AUTHENTIKATE = {**AUTHENTIKATE, "STATIC_TOKENS": {"test": {"sub": "1", "client_id": "oinsoins", "app": "test-app"}}}


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
REKUEST_GRACE = {"DEFAULT": 0, "PER_MODE": {}, "PHYSICAL": 0}

# Point the agent queue at the published dokker redis port (see
# tests/integration/docker-compose.yaml). Replaces the old redis-factory monkeypatch.
AGENT_REDIS_HOST = "localhost"
AGENT_REDIS_PORT = 6666
