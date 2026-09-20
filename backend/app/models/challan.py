from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from ..database import Base


class Challan(Base):
    __tablename__ = "challans"

    id = Column(Integer, primary_key=True, index=True)
    challan_id = Column(String(20), unique=True, index=True, nullable=False)
    violation_id = Column(Integer, ForeignKey("traffic_violations.id"), nullable=False)
    vehicle_number = Column(String(50), nullable=True)
    violation_type = Column(String(50), nullable=False)
    fine_amount = Column(Float, nullable=False)
    detection_timestamp = Column(DateTime, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    evidence_path = Column(String(500), nullable=True)
    ai_confidence = Column(Float, nullable=True)
    verification_status = Column(String(30), nullable=False)
    challan_status = Column(String(30), default="GENERATED")
    officer_id = Column(Integer, ForeignKey("officers.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    violation = relationship("TrafficViolation", back_populates="challan")
    officer = relationship("Officer", back_populates="challans")
