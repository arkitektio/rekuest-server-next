import asyncio
import datetime
import json
import logging
from typing import Optional

import redis
import redis.asyncio as aredis
from authentikate.expand import aexpand_user_from_token, aexpand_client_from_token
from authentikate.utils import authenticate_token_or_none
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings
from facade import models, messages, codes
from facade.persist_backend import persist_backend
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

HEARTBEAT_INTERVAL = settings.AGENT_HEARTBEAT_INTERVAL
HEARTBEAT_RESPONSE_TIMEOUT = settings.AGENT_HEARTBEAT_RESPONSE_TIMEOUT


class FromAgentPayload(BaseModel):
    """Pydantic model representing the payload sent by the agent."""
    message: messages.FromAgentMessage = Field(discriminator="type")


class AgentConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer handling communication with agents."""

    groups = ["broadcast"]

    @classmethod
    def broadcast(cls, agent_id: str, message: messages.ToAgentMessage) -> None:
        """Broadcast a message to a specific agent.

        Args:
            agent_id (str): The identifier of the agent.
            message (messages.ToAgentMessage): The message to send.
        """
        connection = redis.Redis(host="redis")
        connection.lpush(f"{agent_id}_my_queue", message.json())

    async def connect(self) -> None:
        """Handles new WebSocket connection."""
        logger.error("Accepting connection")
        await self.accept()
        print("Connected to agent")
        self.client = None
        self.user = None
        self.registry = None
        self.agent = None
        self.received_initial_payload = False

    async def send_to_agent_message(self, message: messages.ToAgentMessage) -> None:
        """Send a message to the agent.

        Args:
            message (messages.ToAgentMessage): The message to send.
        """
        await self.send(text_data=message.model_dump_json())

    async def on_register(self, register: messages.Register) -> None:
        """Handle agent registration.

        Args:
            register (messages.Register): Registration message from agent.

        Raises:
            ValueError: If the token is invalid.
        """
        logger.error("Registering agent", exc_info=True)
        token = authenticate_token_or_none(register.token)
        if not token:
            raise ValueError("Invalid token")

        self.user = await aexpand_user_from_token(token)
        self.client = await aexpand_client_from_token(token)

        self.registry, _ = await models.Registry.objects.aget_or_create(
            client=self.client,
            user=self.user,
        )

        self.agent, _ = await models.Agent.objects.aget_or_create(
            registry=self.registry,
            instance_id=register.instance_id or "default",
            defaults=dict(
                name=f"{str(self.registry.id)} on {register.instance_id}",
            ),
        )

        self.connection = aredis.Redis(host="redis", auto_close_connection_pool=True)
        self.assignations = await persist_backend.on_agent_connected(self.agent.id)
        self.heartbeat_future: Optional[asyncio.Future] = None

        await self.send_to_agent_message(
            message=messages.Init(
                instance_id=self.agent.instance_id,
                agent=str(self.agent.id),
                registry=str(self.registry.id),
                inquiries=[
                    messages.AssignInquiry(assignation=str(a.id)) for a in self.assignations
                ],
            )
        )

        self.task = asyncio.create_task(self.listen_for_tasks(self.agent.id))
        self.heartbeat_task = asyncio.create_task(self.heartbeat(self.agent.id))
        self.heartbeat_task.add_done_callback(
            lambda x: logging.error(f"Done sending heartbeats {x}")
        )

    async def on_agent_heartbeat(self) -> None:
        """Handle heartbeat message from agent."""
        self.agent.connected = True
        self.agent.last_seen = datetime.datetime.now()
        await self.agent.asave()

        if self.heartbeat_future and not self.heartbeat_future.done():
            logging.debug("ANSWERING HEARTBEAT")
            self.heartbeat_future.set_result(None)
            self.heartbeat_future = None
        else:
            logging.error("Received heartbeat without future, possible race condition.")

    async def heartbeat(self, agent_id: str) -> None:
        """Send periodic heartbeat messages to the agent.

        Args:
            agent_id (str): The ID of the agent.
        """
        try:
            while True:
                await asyncio.sleep(HEARTBEAT_INTERVAL)
                await self.send_to_agent_message(messages.Heartbeat())
                self.heartbeat_future = asyncio.Future()

                try:
                    await asyncio.wait_for(
                        self.heartbeat_future, HEARTBEAT_RESPONSE_TIMEOUT
                    )
                    print("Received heartbeat")

                except asyncio.TimeoutError:
                    logging.error(f"Timeout on client {self.agent.id} for heartbeat")
                    await self.close(code=codes.HEARTBEAT_NOT_RESPONDED_CODE)

        except asyncio.CancelledError:
            return

    async def listen_for_tasks(self, agent_id: str) -> None:
        """Listen for messages in the agent's Redis queue.

        Args:
            agent_id (str): The ID of the agent.
        """
        try:
            while True:
                task = await self.connection.brpoplpush(
                    f"{agent_id}_my_queue", "processing_queue"
                )
                if task:
                    await self.send(text_data=task.decode("utf-8"))
                    await self.connection.lrem("processing_queue", 0, task)
        except asyncio.CancelledError:
            self.connection.close()
            return

    async def receive(self, text_data: Optional[str] = None, bytes_data: Optional[bytes] = None) -> None:
        """Receive and process a message from the WebSocket.

        Args:
            text_data (Optional[str]): Text data from the WebSocket.
            bytes_data (Optional[bytes]): Byte data from the WebSocket.
        """
        try:
            payload = json.loads(text_data)
        except json.JSONDecodeError:
            logger.error("Error in agent", exc_info=True)
            await self.close(code=codes.FROM_AGENT_MESSAGE_IS_NOT_VALID_JSON_CODE)
            return

        try:
            payload = FromAgentPayload(message=payload)
        except Exception:
            logger.error(f"Error in agent {payload}", exc_info=True)
            await self.close(code=codes.FROM_AGENT_MESSAGE_DOES_NOT_MATCH_SCHEMA_CODE)
            return

        try:
            if not self.received_initial_payload:
                if not isinstance(payload.message, messages.Register):
                    raise ValueError("First message must be a register")
                self.received_initial_payload = True
                await self.on_register(payload.message)
            else:
                match payload.message:
                    case messages.Register():
                        await self.on_register(payload.message)
                    case messages.HeartbeatEvent():
                        await self.on_agent_heartbeat()
                    case messages.YieldEvent():
                        await persist_backend.on_agent_yield(
                            self.agent.id, payload.message
                        )
                    case messages.LogEvent():
                        await persist_backend.on_agent_log(
                            self.agent.id, payload.message
                        )
                    case messages.ProgressEvent():
                        await persist_backend.on_agent_progress(
                            self.agent.id, payload.message
                        )
                    case messages.DoneEvent():
                        await persist_backend.on_agent_done(
                            self.agent.id, payload.message
                        )
                    case messages.ErrorEvent():
                        await persist_backend.on_agent_error(
                            self.agent.id, payload.message
                        )
                    case messages.CriticalEvent():
                        await persist_backend.on_agent_critical(
                            self.agent.id, payload.message
                        )
                    case _:
                        logger.error("Error in agent", exc_info=True)
                        await self.close(code=codes.FROM_AGENT_MESSAGE_DOES_NOT_MATCH_SCHEMA_CODE)
                        return
        except Exception:
            logger.error("Error in consumer", exc_info=True)
            await self.close(code=codes.FROM_AGENT_MESSAGE_DOES_NOT_MATCH_SCHEMA_CODE)

    async def disconnect(self, close_code: int) -> None:
        """Handle socket disconnection.

        Args:
            close_code (int): The close code for the WebSocket.
        """
        if hasattr(self, "task"):
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
            except Exception:
                logger.error("Error in consumer", exc_info=True)
                return

        if hasattr(self, "heartbeat_task"):
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass
            except Exception:
                logger.error("Error in consumer", exc_info=True)
                return

        if hasattr(self, "agent") and self.agent:
            await persist_backend.on_agent_disconnected(self.agent.id)

        if hasattr(self, "connection"):
            await self.connection.close()

        logger.warning(f"{self.agent} disconnected with code {close_code}")
