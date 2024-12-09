import asyncio
import datetime
import json
import logging
import uuid

import redis
import redis.asyncio as aredis
from asgiref.sync import sync_to_async
from authentikate import models as auth_models
from authentikate.utils import authenticate_token_or_none
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings
from facade import enums, models
from facade.logic import (
    activate_provision,
    apropagate_provision_change,
    apropagate_reservation_change,
    aset_provision_unprovided,
    schedule_provision,
    schedule_reservation,
)
from facade.persist_backend import persist_backend
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ErrorMessages(BaseModel):
    type = "ERROR"
    error: str
    code: int = 400


class InitialMessage(BaseModel):
    type = "INITIAL"
    instance_id: str = None
    token: str = None


class ProvisionModel(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    provision: str

    def from_provision(provision: models.Provision):
        return ProvisionModel(
            provision=str(provision.id),
        )


class InquiryModel(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    assignation: str

    def from_assignation(assignation: models.Assignation):
        return InquiryModel(
            assignation=str(assignation.id),
        )


class InitMessage(BaseModel):
    type = "INIT"
    instance_id: str = None
    agent: str = None
    registry: str = None
    provisions: list[ProvisionModel] = []
    inquiries: list[InquiryModel] = []
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))


class HeartbeatMessage(BaseModel):
    type = "HEARTBEAT"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))


HEARTBEAT_INTERVAL = settings.AGENT_HEARTBEAT_INTERVAL
HEARTBEAT_RESPONSE_TIMEOUT = settings.AGENT_HEARTBEAT_RESPONSE_TIMEOUT


HEARTBEAT_NOT_RESPONDED_CODE = settings.AGENT_HEARTBEAT_NOT_RESPONDED_CODE


class AgentConsumer(AsyncWebsocketConsumer):
    groups = ["broadcast"]

    @classmethod
    def broadcast(cls, agent_id: str, message: dict):

        connection = redis.Redis(host="redis")

        if not isinstance(message, str):
            message = json.dumps(message)

        connection.lpush(f"{agent_id}_my_queue", message)

    async def connect(self):
        # Called on connection.
        # To accept the connection call:
        await self.accept()

        self.client = None
        self.user = None
        self.registry = None
        self.agent = None
        self.received_initial_payload = False

    async def send_base_model(self, model: BaseModel):
        await self.send(text_data=model.json())

    async def on_initial_payload(self, payload: dict):

        input = InitialMessage(**payload)

        auth = await sync_to_async(authenticate_token_or_none)(input.token)
        if not auth:
            raise ValueError("Invalid token")

        # TODO: Hasch this
        self.registry, _ = await models.Registry.objects.aupdate_or_create(
            app=auth.app,
            user=auth.user,
        )

        self.agent, _ = await models.Agent.objects.aget_or_create(
            registry=self.registry,
            instance_id=input.instance_id or "default",
            defaults=dict(
                name=f"{str(self.registry.id)} on {input.instance_id}",
            ),
        )

        self.connection = aredis.Redis(host="redis", auto_close_connection_pool=True)

        self.agent.status = enums.AgentStatus.ACTIVE
        self.agent.connected = True
        self.agent.last_seen = datetime.datetime.now()
        await self.agent.asave()

        self.answer_future = None

        self.provisions = []
        async for i in models.Provision.objects.filter(agent=self.agent).all():
            self.provisions.append(i)

        self.assignations = []
        async for i in models.Assignation.objects.filter(
            provision__agent=self.agent, status=enums.AssignationEventKind.DISCONNECTED
        ).all():
            self.assignations.append(i)

        await self.send(
            text_data=InitMessage(
                instance_id=input.instance_id,
                agent=str(self.agent.id),
                registry=str(self.registry.id),
                provisions=[ProvisionModel.from_provision(p) for p in self.provisions],
                inquiries=[InquiryModel.from_assignation(p) for p in self.assignations],
            ).json()
        )

        self.task = asyncio.create_task(self.listen_for_tasks(self.agent.id))

        self.heartbeat_task = asyncio.create_task(self.heartbeat(self.agent.id))
        self.heartbeat_task.add_done_callback(
            lambda x: logging.error(f"Done sending heartbeats {x}")
        )

    async def on_agent_heartbeat(self):
        self.agent.last_seen = datetime.datetime.now()
        await self.agent.asave()

    async def heartbeat(self, agent_id: str):
        try:
            while True:
                await asyncio.sleep(HEARTBEAT_INTERVAL)
                await self.send(text_data=HeartbeatMessage().json())

                self.answer_future = asyncio.Future()

                try:
                    received = await asyncio.wait_for(
                        self.answer_future, HEARTBEAT_RESPONSE_TIMEOUT
                    )
                    await self.on_agent_heartbeat()

                except asyncio.TimeoutError:
                    logging.error(f"Timeout on client {self.agent.id} for heatbeat")
                    await self.close(code=HEARTBEAT_NOT_RESPONDED_CODE)

        except asyncio.CancelledError:
            return

    async def listen_for_tasks(self, agent_id: str):
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
            await self.send(text_data=ErrorMessages(error="Invalid JSON").json())
            return

        try:

            if not self.received_initial_payload:
                self.received_initial_payload = True
                await self.on_initial_payload(payload)

            else:

                if payload["type"] == "PROVISION_EVENT":
                    await persist_backend.on_provide_changed(payload)

                if payload["type"] == "ASSIGNATION_EVENT":
                    await persist_backend.on_assign_changed(payload)

                if payload["type"] == "HEARTBEAT":
                    if self.answer_future:
                        logging.debug("ANSWERING HEARTBEAT")
                        self.answer_future.set_result(None)
                    else:
                        logging.error(
                            "Receidved heartbeat without future, holy moly, this is a protocol error"
                        )
                        await self.disconnect(HEARTBEAT_NOT_RESPONDED_CODE)
                        return

        except Exception as e:
            logger.error("Error in consumer", exc_info=True)
            await self.send(text_data=ErrorMessages(error=str(e)).json())
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

        await persist_backend.on_agent_disconnected(self.agent.id)
        pass

        await persist_backend.on_agent_disconnected(self.agent.id)
        pass

        logging.warning(f"{self.agent.id} disconnected with code {close_code}")
