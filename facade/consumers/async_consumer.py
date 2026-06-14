import logging
import uuid
from typing import Optional

from channels.generic.websocket import AsyncWebsocketConsumer

from facade import codes, messages
from facade.consumers.agent_protocol import AgentProtocol
from facade.consumers.agent_queue import RedisAgentQueue

logger = logging.getLogger(__name__)


def _agent_group(agent_id: str) -> str:
    """Channel-layer group holding every live connection for one agent."""
    return f"agent-{agent_id}"


class AgentConsumer(AsyncWebsocketConsumer):
    """Thin Channels adapter around :class:`AgentProtocol`.

    All conversation logic lives in the (transport-agnostic, unit-tested)
    ``AgentProtocol``; this class only wires the WebSocket transport to it and
    manages the connection lifecycle.
    """

    groups = ["broadcast"]

    @classmethod
    def broadcast(cls, agent_id: str, message: messages.ToAgentMessage) -> None:
        """Broadcast a message to a specific agent.

        Producer side of the agent queue: the agent's ``listen_for_tasks`` loop
        relays whatever is pushed here. Synchronous because it is called from the
        backend / signal code.

        Args:
            agent_id (str): The identifier of the agent.
            message (messages.ToAgentMessage): The message to send.
        """
        RedisAgentQueue.from_settings().push(agent_id, message.model_dump_json())

    async def connect(self) -> None:
        """Accept the socket and build a protocol bound to this transport."""
        await self.accept()
        # Identifies this connection within its agent group so a force-register
        # can displace the others without closing itself.
        self.connection_id = str(uuid.uuid4())
        self._agent_group: Optional[str] = None
        self.protocol = AgentProtocol(
            send=lambda text: self.send(text_data=text),
            close=lambda code: self.close(code=code),
            queue=RedisAgentQueue.from_settings(),
            register_connection=self.register_connection,
            kick_others=self.kick_others,
            connection_id=self.connection_id,
        )

    async def register_connection(self, agent_id: str) -> None:
        """Join the agent's connection group once the agent is known."""
        self._agent_group = _agent_group(agent_id)
        await self.channel_layer.group_add(self._agent_group, self.channel_name)

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
        if hasattr(self, "protocol"):
            await self.protocol.shutdown()
        logger.warning(f"Agent disconnected with code {code}")
