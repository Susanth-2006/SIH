from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class NotificationResponse(BaseModel):
    id: int
    officer_id: Optional[int]
    title: str
    message: str
    notification_type: str
    is_read: bool
    related_entity_type: Optional[str]
    related_entity_id: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True
