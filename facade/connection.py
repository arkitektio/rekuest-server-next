import asyncio
from asgiref.sync import async_to_sync
import aiormq
import logging
from django.conf import settings
import pika
import threading
logger = logging.getLogger(__name__)
import redis



import aioredis

redis_pool = redis.ConnectionPool(host='redis', port=6379, db=0)