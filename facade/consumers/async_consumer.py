import asyncio
import datetime
import json
import logging
import uuid
from typing import Union
import redis
import redis.asyncio as aredis
from asgiref.sync import sync_to_async
from authentikate import models as auth_models
from authentikate.utils import authenticate_token_or_none
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings
from facade import enums, models, messages, codes
from facade.persist_backend import persist_backend
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)



HEARTBEAT_INTERVAL = settings.AGENT_HEARTBEAT_INTERVAL
HEARTBEAT_RESPONSE_TIMEOUT = settings.AGENT_HEARTBEAT_RESPONSE_TIMEOUT





class FromAgentPayload(BaseModel):
    message: messages.FromAgentMessage = Field(
        descriminator="type"
    )


class AgentConsumer(AsyncWebsocketConsumer):
    groups = ["broadcast"]

    @classmethod
    def broadcast(cls, agent_id: str, message: messages.ToAgentMessage):
        connection = redis.Redis(host="redis")
        connection.lpush(f"{agent_id}_my_queue", message.json())

    async def connect(self):
        # Called on connection.
        # To accept the connection call:
        await self.accept()

        self.client = None
        self.user = None
        self.registry = None
        self.agent = None
        self.received_initial_payload = False

        
    async def send_to_agent_message(self, message: messages.ToAgentMessage):
        await self.send(text_data=message.json())

    async def on_register(self, register: messages.Register):

        auth = await sync_to_async(authenticate_token_or_none)(register.token)
        if not auth:
            raise ValueError("Invalid token")

        # TODO: Hasch this
        self.registry, _ = await models.Registry.objects.aupdate_or_create(
            app=auth.app,
            user=auth.user,
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
        self.heartbeat_future = None # will be set if a heartbeat was send and unset on receive


        await self.send_to_agent_message(
            message=messages.Init(
                instance_id=self.agent.instance_id,
                agent=str(self.agent.id),
                registry=str(self.registry.id),
                inquiries=[messages.AssignInquiry(assignation=a.id) for a in self.assignations]
            )
        )
        

        self.task = asyncio.create_task(self.listen_for_tasks(self.agent.id))
        self.heartbeat_task = asyncio.create_task(self.heartbeat(self.agent.id))
        self.heartbeat_task.add_done_callback(
            lambda x: logging.error(f"Done sending heartbeats {x}")
        )
        
        

    async def on_agent_heartbeat(self):
        self.agent.connected = True
        self.agent.last_seen = datetime.datetime.now()
        await self.agent.asave()
        if self.heartbeat_future and not self.heartbeat_future.done():
            logging.debug("ANSWERING HEARTBEAT")
            self.heartbeat_future.set_result(None)
            self.heartbeat_future = None
        else:
            logging.error(
                "Receidved heartbeat without future, holy moly, this is a race condition error"
            )
            #await self.disconnect(HEARTBEAT_NOT_RESPONDED_CODE)
            return

    async def heartbeat(self, agent_id: str):
        try:
            while True:
                await asyncio.sleep(HEARTBEAT_INTERVAL)
                await self.send_to_agent_message(messages.Heartbeat())

                self.heartbeat_future = asyncio.Future()

                try:
                    received = await asyncio.wait_for(
                        self.heartbeat_future, HEARTBEAT_RESPONSE_TIMEOUT
                    )
                    print("Received heartbeat", received)

                except asyncio.TimeoutError:
                    logging.error(f"Timeout on client {self.agent.id} for heartbeat")
                    await self.close(code=codes.HEARTBEAT_NOT_RESPONDED_CODE)

        except asyncio.CancelledError:
            return

    async def listen_for_tasks(self, agent_id: str):
        """ Starts listening for message in the queue in
        the redis queue for the agent.
        
        CAVE: messages are already serialized, so we skip
        the serialization step.
        
        
        Args:
            agent_id (str): The id of the agent to listen for tasks
            
        
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

    async def receive(self, text_data=None, bytes_data=None):
        # Called with either text_data or bytes_data for each frame
        # You can call:
        # Or, to send a text frame:
        try:
            payload = json.loads(text_data)
        except json.JSONDecodeError:
            logger.error("Error in agent", exc_info=True)
            await self.close(code=codes.FROM_AGENT_MESSAGE_IS_NOT_VALID_JSON_CODE)
            return
        
        try:
            payload = FromAgentPayload(message=payload)
        except Exception as e:
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
                            self.agent.id,
                            payload.message
                        )
                    case messages.LogEvent():
                        await persist_backend.on_agent_log(
                            self.agent.id,
                            payload.message
                        )
                    case messages.ProgressEvent():
                        await persist_backend.on_agent_progress(
                            self.agent.id,
                            payload.message
                        )

                    case messages.DoneEvent():
                        await persist_backend.on_agent_done(
                            self.agent.id,
                            payload.message
                        )
                    case messages.ErrorEvent():
                        await persist_backend.on_agent_error(
                            self.agent.id,
                            payload.message
                        )
                    case messages.CriticalEvent():
                        await persist_backend.on_agent_critical(
                            self.agent.id,
                            payload.message
                        )
                        
                    case _:
                        logger.error("Error in agent", exc_info=True)
                        await self.close(code=codes.FROM_AGENT_MESSAGE_DOES_NOT_MATCH_SCHEMA_CODE)
                        return
                        
                        

        except Exception as e:
            logger.error("Error in consumer", exc_info=True)
            await self.close(code=codes.FROM_AGENT_MESSAGE_DOES_NOT_MATCH_SCHEMA_CODE)
            return

    async def disconnect(self, close_code):
        # Called when the socket closes

        if hasattr(self, "task"):
            self.task.cancel()

            try:
                await self.task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error("Error in consumer", exc_info=True)
                return

        if hasattr(self, "heartbeat_task"):
            self.heartbeat_task.cancel()

            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error("Error in consumer", exc_info=True)
                return

        if hasattr(self, "agent"):
            if self.agent:
                await persist_backend.on_agent_disconnected(self.agent.id)

        if hasattr(self, "connection"):
            await self.connection.close()
        logging.warning(f"{self.agent} disconnected with code {close_code}")
