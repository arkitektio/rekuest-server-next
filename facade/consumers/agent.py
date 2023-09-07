import ujson
from channels.generic.websocket import AsyncWebsocketConsumer
import logging
from asgiref.sync import sync_to_async
from facade.models import Agent, Registry
from facade.enums import AgentStatus
from .agent_json import *
from urllib.parse import parse_qs
import asyncio
from django.conf import settings
logger = logging.getLogger(__name__)
from .helpers import *
from facade.connection import rmq
from .carrots import *
import aiormq 


THIS_INSTANCE_NAME = settings.INSTANCE_NAME # corresponds to the hostname
KICKED_CLOSE = 3001
BUSY_CLOSE = 3002
BLOCKED_CLOSE = 3003
BOUNCE_CODE = 3004

class AgentBlocked(Exception):
    pass

class AgentKicked(Exception):
    pass

class AgentBusy(Exception):
    pass



denied_codes = [BUSY_CLOSE] # These are codes that should not change the state of the agent


class AgentConsumer(AsyncWebsocketConsumer):
    agent: Agent

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.agent = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.res_queues = {}
        self.res_consumers = {}
        self.res_consumer_tags = {}
        self.prov_queues = {}
        self.prov_consumers = {}
        self.prov_consumer_tags = {}
        self.ass_delivery_tags = {}

    async def connect(self):


        self.channel = await rmq.open_channel()

        self.callback_queue = await self.channel.queue_declare(
            self.agent.queue, auto_delete=True
        )

        logger.info(f"Liustenting Agent on '{self.agent.queue}'")
        # Start listening the queue with name 'hello'
        await self.channel.basic_consume(
            self.callback_queue.queue, self.on_rmq_message_in
        )



        self.queue_length = 5000
        self.incoming_queue = asyncio.Queue(maxsize=self.queue_length)

        try:
            await self.set_agent()
        except AgentBlocked as e:
            logger.error(e)
            await self.close(BLOCKED_CLOSE)
            return
        except AgentBusy as e:
            logger.error(e)
            await self.close(BUSY_CLOSE)
            return
        
        await self.reply(JSONMessage(type=AgentMessageTypes.HELLO))

        replies = await list_provisions(self.agent)
        for reply in replies:
            await self.reply(reply)

        assignations = await list_assignations(self.agent)
        for reply in assignations:
            await self.reply(reply)

        self.incoming_task = asyncio.create_task(self.consumer())



    async def forward(self, f: HareMessage):
        try:
            await self.channel.basic_publish(
                f.to_message(),
                routing_key=f.queue,
            )
        except Exception:
            logger.exception("Error on forward", exc_info=True)

    async def on_rmq_message_in(self, rmq_message: aiormq.abc.DeliveredMessage):
        try:
            json_dict = ujson.loads(rmq_message.body)
            type = json_dict["type"]

            if type == HareMessageTypes.RESERVE:
                await self.on_reserve(ReserveHareMessage(**json_dict))

            if type == HareMessageTypes.KICK:
                await self.on_kick(KickHareMessage(**json_dict))

            if type == HareMessageTypes.BOUNCE:
                await self.on_bounce(BounceHareMessage(**json_dict))

            if type == HareMessageTypes.HEARTBEAT:
                await self.on_heartbeat(HeartbeatHareMessage(**json_dict))


            if type == HareMessageTypes.UNRESERVE:
                await self.on_unreserve(UnreserveHareMessage(**json_dict))

            if type == HareMessageTypes.PROVIDE:
                await self.on_provide(ProvideHareMessage(**json_dict))

            if type == HareMessageTypes.UNPROVIDE:
                await self.on_unprovide(UnprovideHareMessage(**json_dict))

        except Exception:
            logger.exception("Error on on_rmq_message_ins")

        self.channel.basic_ack(rmq_message.delivery.delivery_tag)

    async def on_list_provisions(self, message: ProvisionList):

        replies, forwards = await list_provisions(message, agent=self.agent)

        for r in replies:
            await self.reply(r)

    async def on_list_assignations(self, message: AssignationsList):

        replies, forwards = await list_assignations(message, agent=self.agent)

        for r in replies:
            await self.reply(r)

    async def on_assignment_in(self, provid, rmq_message):
        replies = []
        forwards = []
        try:
            json_dict = ujson.loads(rmq_message.body)
            type = json_dict["type"]


            if type == HareMessageTypes.ASSIGN:
                m = AssignHareMessage(**json_dict)
                self.ass_delivery_tags[m.assignation] = rmq_message.delivery.delivery_tag
                replies, forwards = await bind_assignation(m, provid)

            if type == HareMessageTypes.UNASSIGN:
                m = UnassignHareMessage(**json_dict)
                self.channel.basic_ack(rmq_message.delivery.delivery_tag)
                replies = [UnassignSubMessage(**json_dict)]

        except Exception:
            logger.error("Error on on_assignment_in", exc_info=True)

        logger.debug(f"Received Assignment for {provid} {rmq_message}")

        for r in replies:
            await self.reply(r)

        for r in forwards:
            await self.forward(r)

        
        logger.error(f"OINOINOINOIN Acknowledged Assignment for {provid} {rmq_message}")

    async def on_provision_changed(self, message: ProvisionChangedMessage):

        if message.status == ProvisionStatus.CANCELLED:
            # TODO: SOmehow acknowled this by logging it
            return

        if message.status == ProvisionStatus.ACTIVE:
            replies, forwards, queues, prov_queue = await activate_provision(
                message, agent=self.agent
            )

            for res, queue in queues:
                logger.error(f"Lisenting for queue of Reservation {res}")
                self.res_queues[res] = await self.channel.queue_declare(
                    queue,
                    auto_delete=True,
                )
                tag =  str(uuid.uuid4())
                self.res_consumers[res] = await self.channel.basic_consume(
                    self.res_queues[res].queue,
                    lambda aio: self.on_assignment_in(message.provision, aio),
                    consumer_tag=tag,
                    no_ack=True,
                )
                self.res_consumer_tags[res] = tag



            tag =  str(uuid.uuid4())
            prov_id, prov_queue = prov_queue
            self.prov_queues[prov_id] = await self.channel.queue_declare(
                prov_queue,
                auto_delete=True,
            )
            self.prov_consumers[prov_id] = await self.channel.basic_consume(
                self.prov_queues[prov_id].queue,
                lambda aio: self.on_assignment_in(message.provision, aio),
                consumer_tag=tag,
                no_ack=True,
            )
            self.prov_consumer_tags[prov_id] = tag

        else:
            replies, forwards = await change_provision(message, agent=self.agent)

        for r in forwards:
            await self.forward(r)

        for r in replies:
            await self.reply(r)

    async def on_assignation_changed(self, message: AssignationChangedMessage):

        if message.status == AssignationStatus.ASSIGNED:
            if message.assignation in self.ass_delivery_tags:
                logger.error("Aknowledging this shit")
                self.channel.basic_ack(self.ass_delivery_tags[message.assignation])
            else:
                logger.error("Unaknowledgeablebl")

        replies, forwards = await change_assignation(message, agent=self.agent)
        logger.info(f"Received Assignation for {message.assignation} {forwards}")

        for r in forwards:
            await self.forward(r)

        for r in replies:
            await self.reply(r)

    async def on_reserve(self, message: ReserveHareMessage):

        replies, forwards, reservation_queues = await accept_reservation(
            message, agent=self.agent
        )

        for res, queue in reservation_queues:
            logger.info(f"Lisenting for queue of Reservation {res}")
            self.res_queues[res] = await self.channel.queue_declare(
                queue, auto_delete=True
            )

            await self.channel.basic_consume(
                self.res_queues[res].queue,
                lambda aio: self.on_assignment_in(message.provision, aio),
                consumer_tag=f"res-{res}-prov-{message.provision}",
            )

        for r in forwards:
            await self.forward(r)

        for r in replies:
            await self.reply(r)



    async def on_unreserve(self, message: UnreserveHareMessage):

        replies, forwards, delete_queue_id = await loose_reservation(
            message, agent=self.agent
        )

        for id in delete_queue_id:
            consumer_tag = self.res_consumer_tags[id]
            await self.channel.basic_cancel(consumer_tag)
            logger.debug(
                f"Deleting consumer for queue {id} of Reservation {message.provision}"
            )

        for r in forwards:
            await self.forward(r)

        for r in replies:
            await self.reply(r)

    async def on_provide(self, message: ProvideHareMessage):
        logger.warning(f"Agent received PROVIDE {message}")

        replies = [
            ProvideSubMessage(
                provision=message.provision,
                guardian=message.provision,
                template=message.template,
                status=message.status,
            )
        ]

        for r in replies:
            await self.reply(r)

    async def on_unprovide(self, message: UnprovideHareMessage):
        logger.warning(f"Agent received UNPROVIDE {message}")

        replies = [
            UnprovideSubMessage(
                provision=message.provision,
            )
        ]


        for r in replies:
            await self.reply(r)


        loose_tag = self.prov_consumer_tags[message.provision]
        await self.channel.basic_cancel(loose_tag)
        logger.debug(
            f"Deleting consumer for queue {id} of Provision {message.provision}"
        )


    async def disconnect(self, close_code):

    
        try:
            logger.warning(f"Disconnecting Agent with close_code {close_code}")
            # We are deleting all associated Provisions for this Agent
            forwards = []

            if close_code not in denied_codes:
                forwards = await disconnect_agent(self.agent, close_code)

            for r in forwards:
                await self.forward(r)


            await self.channel.close()
        except Exception as e:
            logger.error(f"Something weird happened in disconnection! {e}")

    async def on_provision_log(self, message):
        await log_to_provision(message, agent=self.agent)

    async def on_assignation_log(self, message):
        await log_to_assignation(message, agent=self.agent)


    @sync_to_async
    def set_agent(self):
        self.client, self.user = self.scope["bounced"].client, self.scope["bounced"].user
        instance_id = (
            parse_qs(self.scope["query_string"])
            .get(b"instance_id", [b"default"])[0]
            .decode("utf8")
        )

        if self.user is None or self.user.is_anonymous:
            registry, _ = Registry.objects.get_or_create(user=None, client=self.client)
        else:
            registry, _ = Registry.objects.get_or_create(user=self.user, client=self.client)

        self.agent, _ = Agent.objects.get_or_create(
            registry=registry, instance_id=instance_id, defaults={"on_instance": THIS_INSTANCE_NAME, "status": AgentStatus.VANILLA}
        )
        if self.agent.status == AgentStatus.ACTIVE:
            raise AgentBusy("Agent already active")
        if self.agent.blocked:
            raise AgentBlocked("Agent blocked. Please unblock it first")

        self.agent.on_instance = THIS_INSTANCE_NAME
        self.agent.status = AgentStatus.ACTIVE
        self.agent.save()

        

    async def receive(self, text_data=None, bytes_data=None):
        self.incoming_queue.put_nowait(
            text_data
        )  # We are buffering here and raise an exception if postman is producing to fast



    async def on_kick(self, message: str):
        print("KICKING")
        await self.close(KICKED_CLOSE)

    async def on_bounce(self, message: str):
        print("IS BOUNCED")
        await self.close(BOUNCE_CODE)




    async def consumer(self):
        try:
            while True:
                text_data = await self.incoming_queue.get()
                json_dict = ujson.loads(text_data)
                type = json_dict["type"]
                if type == AgentMessageTypes.LIST_PROVISIONS:
                    await self.on_list_provisions(ProvisionList(**json_dict))
                if type == AgentMessageTypes.LIST_ASSIGNATIONS:
                    await self.on_list_assignations(AssignationsList(**json_dict))

                if type == AgentMessageTypes.PROVIDE_CHANGED:
                    await self.on_provision_changed(
                        ProvisionChangedMessage(**json_dict)
                    )
                if type == AgentMessageTypes.ASSIGN_CHANGED:
                    await self.on_assignation_changed(
                        AssignationChangedMessage(**json_dict)
                    )

                if type == AgentMessageTypes.ASSIGN_LOG:
                    await self.on_assignation_log(AssignationLogMessage(**json_dict))

                if type == AgentMessageTypes.PROVIDE_LOG:
                    await self.on_provision_log(ProvisionLogMessage(**json_dict))

                self.incoming_queue.task_done()

        except Exception as e:
            logger.critical("Critical Error in handling message in constumer", exc_info=e)
            await self.close(4001)
            raise e

    async def reply(self, m: JSONMessage):  #
        await self.send(text_data=m.json())

    async def on_list_provisions(self, message):
        raise NotImplementedError("Error on this")

    async def on_provision_changed(self, message):
        raise NotImplementedError("Error on this")

    async def on_assignation_changed(self, message):
        raise NotImplementedError("Error on this")

    async def on_assignation_log(self, message):
        raise NotImplementedError("Error on this")

    async def on_provision_log(self, message):
        raise NotImplementedError("Error on this")
