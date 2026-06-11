import logging
from typing import Optional

from channels.generic.websocket import AsyncWebsocketConsumer

from facade import messages
from facade.consumers.agent_protocol import AgentProtocol
from facade.consumers.agent_queue import RedisAgentQueue

logger = logging.getLogger(__name__)


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
        self.protocol = AgentProtocol(
            send=lambda text: self.send(text_data=text),
            close=lambda code: self.close(code=code),
            queue=RedisAgentQueue.from_settings(),
        )

    async def receive(self, text_data: Optional[str] = None, bytes_data: Optional[bytes] = None) -> None:
        """Forward an inbound frame to the protocol."""
        await self.protocol.receive(text_data)

    async def disconnect(self, code: int) -> None:
        """Tear down the protocol's background work on socket close."""
        if hasattr(self, "protocol"):
            await self.protocol.shutdown()
        logger.warning(f"Agent disconnected with code {code}")
