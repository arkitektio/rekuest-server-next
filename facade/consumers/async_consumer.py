from channels.generic.websocket import AsyncWebsocketConsumer
from pydantic import BaseModel
import json
import logging 
from facade import models, enums
from authentikate import models as auth_models
from asgiref.sync import sync_to_async
from authentikate.utils import authenticate_token_or_none

import redis
import asyncio
import redis.asyncio as aredis

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
    id: str
    template: str

    def from_provision(provision: models.Provision):
        return ProvisionModel(
            id=str(provision.id),
            template=provision.template_id,
        )

class ConnectedMessage(BaseModel):
    type = "CONNECTED"
    instance_id: str = None
    agent: str = None
    registry: str = None
    provisions: list[ProvisionModel] = []




class AgentConsumer(AsyncWebsocketConsumer):
    groups = ["broadcast"]


    @classmethod
    def broadcast(cls, agent_id: str, message: dict):

        print("BROADCASTING", agent_id, message)

        connection = redis.Redis(host="redis")

        if not isinstance(message, str):
            message = json.dumps(message)

        connection.lpush(f'{agent_id}_my_queue', message)




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

        self.registry, _ = await models.Registry.objects.aupdate_or_create(
            app=auth.app,
            user= auth.user,
        )

        self.agent, _ = await models.Agent.objects.aupdate_or_create(
            registry=self.registry,
            instance_id=input.instance_id or "default",
            defaults=dict(
                name=f"{str(self.registry.id)} on {input.instance_id}",
            ),
        )

        self.agent.status = enums.AgentStatus.ACTIVE
        await self.agent.asave()


        self.provisions = []
        async for i in models.Provision.objects.filter(agent=self.agent).all():
            self.provisions.append(i)


        await self.send(text_data=ConnectedMessage(
            instance_id=input.instance_id,
            agent=str(self.agent.id),
            registry=str(self.registry.id),
            provisions=[ProvisionModel.from_provision(p) for p in self.provisions]
        ).json()
        )

        print("Connected agent", self.agent.id)
        print("SENT CONNECTED MESSAGE")
        self.__task = asyncio.create_task(self.listen_for_tasks(self.agent.id))
        self.__task.add_done_callback(lambda x: print("DONE", x))

    async def listen_for_tasks(self, agent_id: str):

        connection = aredis.Redis(host="redis", auto_close_connection_pool=False)
        while True:
            task = await connection.brpoplpush(f'{agent_id}_my_queue', 'processing_queue')
            if task:
                print("Receiving", task)
                await self.send(text_data=task.decode("utf-8"))
                await connection.lrem('processing_queue', 0, task)
        
        



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
                return
        

        except Exception as e:
            logger.error("Error in consumer", exc_info=True)
            await self.send(text_data=ErrorMessages(error=str(e)).json())
            return







    async def disconnect(self, close_code):
        # Called when the socket closes

        if self.agent:
            self.agent.status = enums.AgentStatus.DISCONNECTED
            await self.agent.asave()
        print("DISCONNECTED")
        pass

