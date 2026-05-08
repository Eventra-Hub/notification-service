import json
import time
import uuid
import logging
from app.core.redis import client                 
from typing import Optional
from app.models.notification import NotificationOut
logger = logging.getLogger(__name__)
TTL_SECONDS = 60 * 60 * 24 * 7  # 7 days

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
    
    await client.set(notif_id, json.dumps(notification), ex=TTL_SECONDS)

    await client.lpush(list_key, notif_id)

    logger.debug("Stored %s for user %s", notif_id, user_id)
    return notif_id


async def get_notifications(user_id: str) -> list[NotificationOut]:
    
    list_key = f"notif:list:{user_id}"
    keys = await client.lrange(list_key, 0, -1)
    if not keys:
        return []

    values = await client.mget(*keys)
    result = []
    for v in values:
        if v is None:
            continue
        result.append(NotificationOut(**json.loads(v)))
    return result