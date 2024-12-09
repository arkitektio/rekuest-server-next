import asyncio
from asgiref.sync import async_to_sync
import aiormq
import logging
from django.conf import settings
import pika
import threading

logger = logging.getLogger(__name__)
import redis
from typing import Protocol


import aioredis

redis_pool = redis.ConnectionPool(host="redis", port=6379, db=0)


class SyncConnection(Protocol):

    def publish(self, queue, message):
        pass


class AsyncConnection(Protocol):

    async def apublish(self, queue, message):
        pass


class RabbitMQConnection:

    def publish(self, queue, message):
        connection = pika.BlockingConnection(pika.ConnectionParameters(host="rabbitmq"))
        channel = connection.channel()
        channel.queue_declare(queue=queue)
        channel.basic_publish(exchange="", routing_key=queue, body=message)
        connection.close()


class AsyncRabbitMQConnection:

    def apublish(self, queue, message):
        pass


def create_sync_connection() -> SyncConnection:
    return RabbitMQConnection()


def create_async_connection() -> AsyncConnection:
    return RabbitMQConnection()
