import asyncio
import aio_pika
from app.core.config import settings

EXCHANGE_NAME = "events.exchange"

connection = None
channel = None
exchange = None
queue = None
_consumer_task = None

async def _on_message(message: aio_pika.IncomingMessage):
    async with message.process():
        # logic intentionally left out
        pass

async def connect_rabbitmq():
    global connection, channel, exchange, queue, _consumer_task
    connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=10)

    exchange = await channel.declare_exchange(
        EXCHANGE_NAME, aio_pika.ExchangeType.TOPIC, durable=True
    )
    queue = await channel.declare_queue(settings.QUEUE_NAME, durable=True)
    await queue.bind(exchange, routing_key="#")

    _consumer_task = asyncio.create_task(queue.consume(_on_message))

async def close_rabbitmq():
    global connection
    if connection:
        await connection.close()
