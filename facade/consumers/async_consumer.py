import logging
import uuid
from typing import Optional

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from facade import caller_events, codes, messages, models
from facade.consumers.agent_protocol import AgentProtocol
from facade.consumers.agent_queue import RedisAgentQueue

logger = logging.getLogger(__name__)


def _agent_group(agent_id: str) -> str:
    """Channel-layer group holding every live connection for one agent."""
    return f"agent-{agent_id}"


def _caller_group(caller_id: str) -> str:
    """Channel-layer group carrying the assignation events a caller originated."""
    return f"ass_caller_{caller_id}"


class AgentConsumer(AsyncWebsocketConsumer):
    """Thin Channels adapter around :class:`AgentProtocol`.

    All conversation logic lives in the (transport-agnostic, unit-tested)
    ``AgentProtocol``; this class only wires the WebSocket transport to it and
    manages the connection lifecycle.
    """

    groups = ["broadcast"]

    @classmethod
    def broadcast(cls, agent_id: int, message: messages.ToAgentMessage) -> None:
        """Send a message to a specific agent over its transport (thin facade).

        Kept for the existing backend/signal call sites; delegates to the typed
        :func:`facade.transport.deliver_to_agent`, which picks redis queue (WEBSOCKET) vs
        HMAC-signed POST (WEBHOOK). Called only AFTER the row is persisted, so a failed
        delivery is recoverable from the DB.
        """
        from facade import transport  # lazy: transport imports this consumer's queue module

        agent = models.Agent.objects.only("id", "kind", "hook_url", "hook_url_secret").get(id=agent_id)
        transport.deliver_to_agent(agent, message)

    async def connect(self) -> None:
        """Accept the socket and build a protocol bound to this transport."""
        await self.accept()
        # Identifies this connection within its agent group so a force-register
        # can displace the others without closing itself.
        self.connection_id = str(uuid.uuid4())
        self._agent_group: Optional[str] = None
        self._caller_group: Optional[str] = None
        self.protocol = AgentProtocol(
            send=lambda text: self.send(text_data=text),
            close=lambda code: self.close(code=code),
            queue=RedisAgentQueue.from_settings(),
            register_connection=self.register_connection,
            kick_others=self.kick_others,
            register_caller=self.register_caller,
            connection_id=self.connection_id,
        )

    async def register_connection(self, agent_id: str) -> None:
        """Join the agent's connection group once the agent is known."""
        self._agent_group = _agent_group(agent_id)
        await self.channel_layer.group_add(self._agent_group, self.channel_name)

    async def register_caller(self, caller_id: str) -> None:
        """Join the caller event group so events of work this identity originated reach us."""
        self._caller_group = _caller_group(caller_id)
        await self.channel_layer.group_add(self._caller_group, self.channel_name)

    async def channel_AssignationEventCreatedEvent(self, event: dict) -> None:
        """Forward a caller-bound assignation event to this socket as a ``…Event`` mirror.

        Producer side: ``facade/signals.py`` broadcasts ``AssignationEventCreatedEvent`` to
        ``ass_caller_{caller_id}`` on every Assignation/AssignationEvent save (the same group
        the GraphQL subscription consumes). We only forward the ``event`` branch — the
        ``create`` branch is covered authoritatively by ``AssignResponse``, so forwarding
        it too would race the ack. Best-effort: a brief disconnect simply misses events.
        """
        protocol = getattr(self, "protocol", None)
        if protocol is None or protocol.session is None:
            return  # not registered yet — nothing to correlate against

        event_id = (event.get("message") or {}).get("event")
        if event_id is None:
            return  # a `create` (or malformed) payload — not an assignation event

        message = await self._build_execution_event(event_id)
        if message is not None:
            await protocol.send_to_agent_message(message)

    @database_sync_to_async
    def _build_execution_event(self, event_id):
        """Load the AssignationEvent and map it to its …Event mirror (off the event loop)."""
        try:
            event = models.AssignationEvent.objects.select_related("assignation").get(id=event_id)
        except models.AssignationEvent.DoesNotExist:
            return None
        return caller_events.build_execution_event(event)

    async def kick_others(self) -> None:
        """Tell every other connection in this agent's group to close."""
        if self._agent_group is None:
            return
        await self.channel_layer.group_send(
            self._agent_group,
            {"type": "agent.displace", "initiator": self.connection_id},
        )

    async def agent_displace(self, event: dict) -> None:
        """Channel-layer handler: close unless we initiated the displacement."""
        if event.get("initiator") != self.connection_id:
            await self.close(code=codes.AGENT_REPLACED_CODE)

    async def receive(self, text_data: Optional[str] = None, bytes_data: Optional[bytes] = None) -> None:
        """Forward an inbound frame to the protocol."""
        await self.protocol.receive(text_data)

    async def disconnect(self, code: int) -> None:
        """Tear down the protocol's background work on socket close."""
        group = getattr(self, "_agent_group", None)
        if group is not None:
            await self.channel_layer.group_discard(group, self.channel_name)
        caller_group = getattr(self, "_caller_group", None)
        if caller_group is not None:
            await self.channel_layer.group_discard(caller_group, self.channel_name)
        if hasattr(self, "protocol"):
            await self.protocol.shutdown()
        logger.warning(f"Agent disconnected with code {code}")
