from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database import get_db
from ..models.notification import Notification
from ..schemas.notification import NotificationResponse
from ..services.notification_service import get_unread_notifications, mark_notification_read

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("/", response_model=List[NotificationResponse])
def list_notifications(
    skip: int = 0,
    limit: int = 50,
    is_read: Optional[bool] = None,
    officer_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Notification)
    if is_read is not None:
        query = query.filter(Notification.is_read == is_read)
    if officer_id:
        query = query.filter(Notification.officer_id == officer_id)
    return query.order_by(Notification.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/unread", response_model=List[NotificationResponse])
def list_unread(officer_id: Optional[int] = None, db: Session = Depends(get_db)):
    return get_unread_notifications(db, officer_id)


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
def read_notification(notification_id: int, db: Session = Depends(get_db)):
    notification = mark_notification_read(db, notification_id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notification


@router.patch("/read-all")
def read_all_notifications(db: Session = Depends(get_db)):
    db.query(Notification).filter(Notification.is_read == False).update({"is_read": True})
    db.commit()
    return {"detail": "All notifications marked as read"}
