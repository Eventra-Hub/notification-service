import asyncio
import aio_pika
import logging
import json
from app.core.config import settings

EXCHANGE_NAME = "events.exchange"

connection = None
channel = None
exchange = None
queue = None
_consumer_task = None

logger = logging.getLogger(__name__)

async def _on_message(message: aio_pika.IncomingMessage):
    async with message.process():
        try:
            payload = json.loads(message.body.decode("utf-8"))
            user_id           = payload.get("user_id")
            msg_text          = payload.get("message")
            notification_type = payload.get("notification_type", "GENERAL")
            event_id          = payload.get("event_id")
            if not user_id or not msg_text:
                logger.warning("Skipping message — missing user_id or message: %s", payload)
                return
            
            from app.services.notification_store import store_notification
            notif_id = await store_notification(
                user_id=user_id,
                message=msg_text,
                notification_type=notification_type,
                event_id=event_id,
            )
            logger.info(json.dumps({
                "event":           "notification_stored",
                "notification_id": notif_id,
                "user_id":         user_id,
                "type":            notification_type,
            }))
        except json.JSONDecodeError as e:
            logger.error("Bad JSON in message body: %s", e)
        except Exception as e:
            logger.error("Unhandled error in _on_message: %s", e)
                        # Never re-raise — crashing here kills the consumer task

async def connect_rabbitmq():
    global connection, channel, exchange, queue, _consumer_task
    connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
    channel    = await connection.channel()
    await channel.set_qos(prefetch_count=10)
    exchange   = await channel.declare_exchange(
        EXCHANGE_NAME, aio_pika.ExchangeType.TOPIC, durable=True
    )
    queue = await channel.declare_queue(settings.QUEUE_NAME, durable=True)
    await queue.bind(exchange, routing_key="#")
    _consumer_task = asyncio.create_task(queue.consume(_on_message))
    logger.info("RabbitMQ consumer started on queue: %s", settings.QUEUE_NAME)

async def close_rabbitmq():
    global connection, _consumer_task
    if _consumer_task:
        _consumer_task.cancel()
    if connection:
        await connection.close()
    logger.info("RabbitMQ connection closed")
