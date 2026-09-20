from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from ..database import Base


class Pothole(Base):
    __tablename__ = "potholes"

    id = Column(Integer, primary_key=True, index=True)
    pothole_id = Column(String(20), unique=True, index=True, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    severity = Column(String(20), default="medium")
    confidence = Column(Float, nullable=False)
    status = Column(String(30), default="DETECTED")
    detected_by_vehicle_id = Column(Integer, ForeignKey("fleet_vehicles.id"), nullable=True)
    video_job_id = Column(String(40), nullable=True)
    evidence_image = Column(String(500), nullable=True)
    evidence_video = Column(String(500), nullable=True)
    detection_details = Column(Text, nullable=True)
    duplicate_of_id = Column(Integer, ForeignKey("potholes.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    detected_by_vehicle = relationship("FleetVehicle", back_populates="potholes_detected", foreign_keys=[detected_by_vehicle_id])
    verifications = relationship("PotholeVerification", back_populates="pothole", cascade="all, delete-orphan")
    duplicate_of = relationship("Pothole", remote_side=[id], backref="duplicates")


class PotholeVerification(Base):
    __tablename__ = "pothole_verifications"

    id = Column(Integer, primary_key=True, index=True)
    pothole_id = Column(Integer, ForeignKey("potholes.id"), nullable=False)
    officer_id = Column(Integer, ForeignKey("officers.id"), nullable=True)
    action = Column(String(30), nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    pothole = relationship("Pothole", back_populates="verifications")
    officer = relationship("Officer", back_populates="pothole_verifications")
