"""Transport port for the agent message queue.

The agent delivery path (backend ``broadcast`` -> agent socket) is a hand-rolled
redis queue rather than the Channels channel layer, on purpose: a message
pushed while the agent is offline persists in redis and survives reconnect,
which ``group_send`` to an empty group would drop.

``AgentQueue`` makes that swappable so the consumer can run against a real redis
in integration tests and against an in-memory fake in pure unit tests, without
monkeypatching the ``redis``/``redis.asyncio`` factories.
"""

import abc
import asyncio
from collections import defaultdict
from typing import DefaultDict, Dict, Optional, Tuple

import redis
import redis.asyncio as aredis
from django.conf import settings

QUEUE_SUFFIX = "_my_queue"
PROCESSING_SUFFIX = "_processing"


def _processing_key(agent_id: str) -> str:
    """The per-agent in-flight list — scopes ``ack``/recovery to one agent."""
    return f"{agent_id}{PROCESSING_SUFFIX}"


# Reuse one sync connection pool per (host, port) across all the short-lived
# ``RedisAgentQueue`` instances that ``broadcast`` creates — otherwise every
# pushed message would open and tear down a fresh TCP connection.
_sync_pools: Dict[Tuple[str, int], "redis.ConnectionPool"] = {}


def _sync_pool(host: str, port: int) -> "redis.ConnectionPool":
    key = (host, port)
    pool = _sync_pools.get(key)
    if pool is None:
        pool = redis.ConnectionPool(host=host, port=port)
        _sync_pools[key] = pool
    return pool


class AgentQueue(abc.ABC):
    """A per-agent message queue: producers ``push``, the consumer ``pop``s."""

    @abc.abstractmethod
    def push(self, agent_id: str, message_json: str) -> None:
        """Enqueue a (already serialized) message for ``agent_id``.

        Synchronous: it is called from the backend / signal code (and from the
        classmethod ``AgentConsumer.broadcast``) which runs in a sync context.
        """

    @abc.abstractmethod
    async def pop(self, agent_id: str) -> Optional[str]:
        """Block until a message is available for ``agent_id`` and return it.

        The message is moved to an in-flight holding area, NOT removed — the
        caller must ``ack`` it once it has been delivered. This send-then-ack
        ordering keeps delivery at-least-once: a crash between ``pop`` and
        ``ack`` leaves the message recoverable rather than lost.
        """

    @abc.abstractmethod
    async def ack(self, agent_id: str, message: str) -> None:
        """Acknowledge a message returned by ``pop`` (remove it from in-flight).

        ``agent_id`` scopes the removal to that agent's in-flight area.
        """

    @abc.abstractmethod
    async def close(self) -> None:
        """Release any underlying connections."""


class RedisAgentQueue(AgentQueue):
    """Redis-backed queue reproducing the original ``lpush``/``blmove`` flow."""

    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self._async_connection: Optional[aredis.Redis] = None

    @classmethod
    def from_settings(cls) -> "RedisAgentQueue":
        return cls(host=settings.AGENT_REDIS_HOST, port=settings.AGENT_REDIS_PORT)

    def push(self, agent_id: str, message_json: str) -> None:
        # Pooled connection: returned to the pool on use, not torn down per call.
        connection = redis.Redis(connection_pool=_sync_pool(self.host, self.port))
        connection.lpush(f"{agent_id}{QUEUE_SUFFIX}", message_json)

    async def pop(self, agent_id: str) -> Optional[str]:
        if self._async_connection is None:
            self._async_connection = aredis.Redis(host=self.host, port=self.port)

        # Move into this agent's processing list but leave it there; ``ack``
        # removes it only after the caller has delivered the message.
        task = await self._async_connection.blmove(f"{agent_id}{QUEUE_SUFFIX}", _processing_key(agent_id), timeout=0, src="RIGHT", dest="LEFT")
        if task is None:
            return None
        return task.decode("utf-8")

    async def ack(self, agent_id: str, message: str) -> None:
        if self._async_connection is not None:
            await self._async_connection.lrem(_processing_key(agent_id), 0, message)

    async def close(self) -> None:
        if self._async_connection is not None:
            await self._async_connection.aclose()
            self._async_connection = None


class InMemoryAgentQueue(AgentQueue):
    """In-process queue for unit tests — no redis, no network."""

    def __init__(self) -> None:
        self._queues: DefaultDict[str, "asyncio.Queue[str]"] = defaultdict(asyncio.Queue)

    def push(self, agent_id: str, message_json: str) -> None:
        self._queues[agent_id].put_nowait(message_json)

    async def pop(self, agent_id: str) -> Optional[str]:
        return await self._queues[agent_id].get()

    async def ack(self, agent_id: str, message: str) -> None:
        # ``asyncio.Queue.get`` already removed the item; nothing to do.
        return None

    async def close(self) -> None:
        return None
