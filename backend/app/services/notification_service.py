from sqlalchemy.orm import Session
from ..models.notification import Notification
from ..models.officer import Officer


def create_notification(
    db: Session,
    title: str,
    message: str,
    notification_type: str,
    officer_id: int = None,
    related_entity_type: str = None,
    related_entity_id: int = None,
) -> Notification:
    notification = Notification(
        officer_id=officer_id,
        title=title,
        message=message,
        notification_type=notification_type,
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def get_unread_notifications(db: Session, officer_id: int = None):
    query = db.query(Notification).filter(Notification.is_read == False)
    if officer_id:
        query = query.filter(Notification.officer_id == officer_id)
    return query.order_by(Notification.created_at.desc()).all()


def mark_notification_read(db: Session, notification_id: int):
    notification = db.query(Notification).filter(Notification.id == notification_id).first()
    if notification:
        notification.is_read = True
        db.commit()
        db.refresh(notification)
    return notification
