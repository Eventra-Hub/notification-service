from fastapi import APIRouter, HTTPException
from app.models.notification import NotificationIn, NotificationOut, SendResponse
from app.services.notification_store import store_notification, get_notifications
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# POST /notifications/send 
@router.post("/send", response_model=SendResponse, status_code=200)
async def send_notification(body: NotificationIn):
    try:
        notif_id = await store_notification(
            user_id=body.user_id,
            message=body.message,
            notification_type=body.notification_type.value,
            event_id=body.event_id
        )
        return SendResponse(status="sent", notification_id=notif_id)
    except Exception as e:
        logger.error("store_notification failed: %s", e)
        raise HTTPException(status_code=500, detail="Failed to store notification")


#  GET /notifications/user/{user_id} (Returns the user's notification history from Redis, newest first)
@router.get("/user/{user_id}", response_model=list[NotificationOut])
async def get_user_notifications(user_id: str):
    try:
        return await get_notifications(user_id)
    except Exception as e:
        logger.exception("get_notifications failed for user %s: %s", user_id, e)
        raise HTTPException(status_code=500, detail=f"Failed to fetch notifications: {e}")

#  GET /notifications/health 
@router.get("/health")
async def router_health():
    return {"status": "ok"}