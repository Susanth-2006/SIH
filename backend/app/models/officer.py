from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from ..database import Base


class Officer(Base):
    __tablename__ = "officers"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    email = Column(String(100), nullable=True)
    password_hash = Column(String(255), nullable=True)
    role = Column(String(50), default="officer")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    pothole_verifications = relationship("PotholeVerification", back_populates="officer")
    verified_violations = relationship("TrafficViolation", back_populates="verified_by_officer", foreign_keys="TrafficViolation.verified_by_officer_id")
    challans = relationship("Challan", back_populates="officer")
    notifications = relationship("Notification", back_populates="officer")
