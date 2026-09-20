from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from ..database import Base


class TrafficViolation(Base):
    __tablename__ = "traffic_violations"

    id = Column(Integer, primary_key=True, index=True)
    violation_id = Column(String(20), unique=True, index=True, nullable=False)
    violation_type = Column(String(50), nullable=False)
    vehicle_number = Column(String(50), nullable=True)
    timestamp = Column(DateTime, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    confidence = Column(Float, nullable=False)
    evidence_image = Column(String(500), nullable=True)
    evidence_video = Column(String(500), nullable=True)
    detection_details = Column(Text, nullable=True)
    detected_by_vehicle_id = Column(Integer, ForeignKey("fleet_vehicles.id"), nullable=True)
    video_job_id = Column(String(40), nullable=True)
    status = Column(String(30), default="AI_DETECTED")
    verification_status = Column(String(30), default="AI_VERIFIED")
    fine_amount = Column(Float, default=0.0)
    challan_status = Column(String(30), default="NOT_GENERATED")
    verified_by_officer_id = Column(Integer, ForeignKey("officers.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    detected_by_vehicle = relationship("FleetVehicle", back_populates="violations_detected", foreign_keys=[detected_by_vehicle_id])
    evidence_records = relationship("TrafficEvidence", back_populates="violation", cascade="all, delete-orphan")
    challan = relationship("Challan", back_populates="violation", uselist=False, cascade="all, delete-orphan")
    verified_by_officer = relationship("Officer", back_populates="verified_violations", foreign_keys=[verified_by_officer_id])


class TrafficEvidence(Base):
    __tablename__ = "traffic_evidence"

    id = Column(Integer, primary_key=True, index=True)
    violation_id = Column(Integer, ForeignKey("traffic_violations.id"), nullable=False)
    evidence_type = Column(String(20), nullable=False)
    file_path = Column(String(500), nullable=False)
    timestamp = Column(DateTime, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    vehicle_number = Column(String(50), nullable=True)
    violation_type = Column(String(50), nullable=True)
    confidence = Column(Float, nullable=True)
    ocr_result = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    violation = relationship("TrafficViolation", back_populates="evidence_records")
