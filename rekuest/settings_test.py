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
