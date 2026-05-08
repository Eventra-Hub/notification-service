from pydantic import BaseModel
from typing import Optional
from enum import Enum

class NotificationType(str, Enum):
    # These values must match exactly what M3 sends in notification_type
    BOOKING_CONFIRMED = "BOOKING_CONFIRMED"
    BOOKING_CANCELLED = "BOOKING_CANCELLED"
    EVENT_REMINDER    = "EVENT_REMINDER"

class NotificationIn(BaseModel):
    """
    Body for POST /notifications/send.
    Fields match the agreed payload from Registration service:
      { user_id, message, notification_type, event_id }
    """
    user_id:           str
    message:           str
    notification_type: NotificationType
    event_id:          Optional[str] = None

class NotificationOut(BaseModel):
    """Shape returned by GET /notifications/user/{user_id}."""
    notification_id:   str
    user_id:           str
    message:           str
    notification_type: str
    event_id:          Optional[str]
    timestamp:         int
    read:              bool

class SendResponse(BaseModel):
    status:          str  
    notification_id: str