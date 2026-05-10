import json
import time
import uuid
import logging
from app.core import redis as redis_module
from typing import Optional
from app.models.notification import NotificationOut

logger = logging.getLogger(__name__)

TTL_SECONDS = 60 * 60 * 24 * 7   # 7 days
MAX_LIST_LEN = 200                # cap per-user history


async def store_notification(
    user_id:           str,
    message:           str,
    notification_type: str,
    event_id:          Optional[str] = None,
) -> str:

    notif_id = f"notif:{user_id}:{uuid.uuid4().hex[:12]}"
    list_key = f"notif:list:{user_id}"

    notification = {
        "notification_id":   notif_id,
        "user_id":           user_id,
        "message":           message,
        "notification_type": notification_type,
        "event_id":          event_id,
        "timestamp":         int(time.time()),
        "read":              False,
    }

    client = redis_module.client
    if client is None:
        raise RuntimeError("Redis client is not initialized")

    pipe = client.pipeline(transaction=False)
    pipe.set(notif_id, json.dumps(notification), ex=TTL_SECONDS)
    pipe.lpush(list_key, notif_id)
    pipe.ltrim(list_key, 0, MAX_LIST_LEN - 1)
    pipe.expire(list_key, TTL_SECONDS)
    await pipe.execute()

    logger.debug("Stored %s for user %s", notif_id, user_id)
    return notif_id


async def get_notifications(user_id: str) -> list[NotificationOut]:
    client = redis_module.client
    if client is None:
        logger.error("Redis client is not initialized")
        return []

    list_key = f"notif:list:{user_id}"
    keys = await client.lrange(list_key, 0, -1)
    if not keys:
        return []

    values = await client.mget(*keys)

    result: list[NotificationOut] = []
    stale: list[str] = []

    for k, v in zip(keys, values):
        if v is None:
            stale.append(k)
            continue
        try:
            result.append(NotificationOut(**json.loads(v)))
        except Exception as e:
            logger.warning("Skipping malformed notification %s: %s", k, e)
            stale.append(k)

    if stale:
        pipe = client.pipeline(transaction=False)
        for k in stale:
            pipe.lrem(list_key, 0, k)
        try:
            await pipe.execute()
        except Exception as e:
            logger.warning("Failed to prune stale ids for %s: %s", user_id, e)

    return result
