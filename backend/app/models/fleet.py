from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from ..database import Base


class FleetVehicle(Base):
    __tablename__ = "fleet_vehicles"

    id = Column(Integer, primary_key=True, index=True)
    fleet_id = Column(String(50), unique=True, index=True, nullable=False)
    vehicle_number = Column(String(50), nullable=False)
    vehicle_type = Column(String(50), default="bus")
    current_lat = Column(Float, nullable=True)
    current_lng = Column(Float, nullable=True)
    route_name = Column(String(100), nullable=True)
    camera_status = Column(String(20), default="active")
    gps_status = Column(String(20), default="active")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    gps_points = relationship("GPSPoint", back_populates="vehicle", cascade="all, delete-orphan")
    potholes_detected = relationship("Pothole", back_populates="detected_by_vehicle", foreign_keys="Pothole.detected_by_vehicle_id")
    violations_detected = relationship("TrafficViolation", back_populates="detected_by_vehicle", foreign_keys="TrafficViolation.detected_by_vehicle_id")


class GPSPoint(Base):
    __tablename__ = "gps_points"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("fleet_vehicles.id"), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    speed = Column(Float, nullable=True)
    heading = Column(Float, nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    vehicle = relationship("FleetVehicle", back_populates="gps_points")
