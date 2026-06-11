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
from typing import DefaultDict, Optional

import redis
import redis.asyncio as aredis
from django.conf import settings

QUEUE_SUFFIX = "_my_queue"
PROCESSING_QUEUE = "processing_queue"


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
    async def ack(self, message: str) -> None:
        """Acknowledge a message returned by ``pop`` (remove it from in-flight)."""

    @abc.abstractmethod
    async def close(self) -> None:
        """Release any underlying connections."""


class RedisAgentQueue(AgentQueue):
    """Redis-backed queue reproducing the original ``lpush``/``brpoplpush`` flow."""

    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self._async_connection: Optional[aredis.Redis] = None

    @classmethod
    def from_settings(cls) -> "RedisAgentQueue":
        return cls(host=settings.AGENT_REDIS_HOST, port=settings.AGENT_REDIS_PORT)

    def push(self, agent_id: str, message_json: str) -> None:
        connection = redis.Redis(host=self.host, port=self.port)
        try:
            connection.lpush(f"{agent_id}{QUEUE_SUFFIX}", message_json)
        finally:
            connection.close()

    async def pop(self, agent_id: str) -> Optional[str]:
        if self._async_connection is None:
            self._async_connection = aredis.Redis(
                host=self.host, port=self.port, auto_close_connection_pool=True
            )

        # Move into the processing queue but leave it there; ``ack`` removes it
        # only after the caller has delivered the message.
        task = await self._async_connection.brpoplpush(f"{agent_id}{QUEUE_SUFFIX}", PROCESSING_QUEUE)
        if task is None:
            return None
        return task.decode("utf-8")

    async def ack(self, message: str) -> None:
        if self._async_connection is not None:
            await self._async_connection.lrem(PROCESSING_QUEUE, 0, message)

    async def close(self) -> None:
        if self._async_connection is not None:
            await self._async_connection.close()
            self._async_connection = None


class InMemoryAgentQueue(AgentQueue):
    """In-process queue for unit tests — no redis, no network."""

    def __init__(self) -> None:
        self._queues: DefaultDict[str, "asyncio.Queue[str]"] = defaultdict(asyncio.Queue)

    def push(self, agent_id: str, message_json: str) -> None:
        self._queues[agent_id].put_nowait(message_json)

    async def pop(self, agent_id: str) -> Optional[str]:
        return await self._queues[agent_id].get()

    async def ack(self, message: str) -> None:
        # ``asyncio.Queue.get`` already removed the item; nothing to do.
        return None

    async def close(self) -> None:
        return None
