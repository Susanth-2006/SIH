from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
from ..database import get_db
from ..models.pothole import Pothole
from ..models.traffic_violation import TrafficViolation
from ..models.fleet import FleetVehicle
from ..utils.helpers import generate_id, next_id
from ..services.notification_service import create_notification
from ..config import settings
import os
import uuid
import json
import math
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/demo", tags=["demo"])


class SimulateFleetRequest(BaseModel):
    vehicle_id: int
    start_lat: float = 17.3850
    start_lng: float = 78.4867
    end_lat: float = 17.3950
    end_lng: float = 78.4967
    num_points: int = 20


class AddPotholeRequest(BaseModel):
    latitude: float = 17.3850
    longitude: float = 78.4867
    severity: str = "medium"
    confidence: float = 0.85
    detected_by_vehicle_id: Optional[int] = None


class AddViolationRequest(BaseModel):
    violation_type: str = "NO_HELMET"
    vehicle_number: str = "TS09XXXX"
    latitude: float = 17.3850
    longitude: float = 78.4867
    confidence: float = 0.92
    detected_by_vehicle_id: Optional[int] = None


@router.post("/simulate-fleet")
def simulate_fleet_movement(req: SimulateFleetRequest, db: Session = Depends(get_db)):
    vehicle = db.query(FleetVehicle).filter(FleetVehicle.id == req.vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    from ..models.fleet import GPSPoint
    from datetime import datetime, timezone

    points_created = []
    for i in range(req.num_points):
        frac = i / max(req.num_points - 1, 1)
        lat = req.start_lat + (req.end_lat - req.start_lat) * frac
        lng = req.start_lng + (req.end_lng - req.start_lng) * frac
        lat += (hash(f"{req.vehicle_id}-{i}") % 100 - 50) * 0.00001
        lng += (hash(f"{req.vehicle_id}-{i}-lng") % 100 - 50) * 0.00001

        point = GPSPoint(
            vehicle_id=req.vehicle_id,
            latitude=lat,
            longitude=lng,
            speed=30 + (i % 20),
            heading=(i * 18) % 360,
            timestamp=datetime.now(timezone.utc) - timedelta(minutes=req.num_points - i),
        )
        db.add(point)
        points_created.append(point)

    last_point = points_created[-1]
    vehicle.current_lat = last_point.latitude
    vehicle.current_lng = last_point.longitude

    db.commit()
    return {"detail": f"Simulated {req.num_points} GPS points for {vehicle.fleet_id}", "points_created": req.num_points}


@router.post("/add-pothole")
def add_demo_pothole(req: AddPotholeRequest, db: Session = Depends(get_db)):
    pothole = Pothole(
        pothole_id=next_id(db, Pothole, "pothole_id", "PH"),
        latitude=req.latitude,
        longitude=req.longitude,
        severity=req.severity,
        confidence=req.confidence,
        detected_by_vehicle_id=req.detected_by_vehicle_id,
        status="VERIFIED" if req.confidence >= settings.CONFIDENCE_THRESHOLD else "PENDING_VERIFICATION",
    )
    db.add(pothole)
    db.commit()
    db.refresh(pothole)
    return pothole


@router.post("/add-violation")
def add_demo_violation(req: AddViolationRequest, db: Session = Depends(get_db)):
    violation = TrafficViolation(
        violation_id=next_id(db, TrafficViolation, "violation_id", "TV"),
        violation_type=req.violation_type,
        vehicle_number=req.vehicle_number,
        timestamp=datetime.utcnow(),
        latitude=req.latitude,
        longitude=req.longitude,
        confidence=req.confidence,
        detected_by_vehicle_id=req.detected_by_vehicle_id,
        status="AI_DETECTED",
        verification_status="AI_VERIFIED" if req.confidence >= settings.CONFIDENCE_THRESHOLD else "PENDING_OFFICER",
    )
    db.add(violation)
    db.commit()
    db.refresh(violation)
    return violation


@router.post("/seed")
def seed_demo_data(db: Session = Depends(get_db)):
    existing_vehicles = db.query(FleetVehicle).count()
    if existing_vehicles == 0:
        vehicles_data = [
            ("F-101", "TS09AB1234", "bus", "Route A - Central"),
            ("F-102", "TS09CD5678", "bus", "Route B - East"),
            ("F-103", "TS09EF9012", "bus", "Route C - West"),
            ("F-104", "TS09GH3456", "van", "Route D - North"),
            ("F-105", "TS09IJ7890", "car", "Route E - South"),
        ]
        for fleet_id, vnum, vtype, route in vehicles_data:
            v = FleetVehicle(
                fleet_id=fleet_id,
                vehicle_number=vnum,
                vehicle_type=vtype,
                route_name=route,
                current_lat=17.3850 + (hash(fleet_id) % 100) * 0.0001,
                current_lng=78.4867 + (hash(fleet_id + "lng") % 100) * 0.0001,
            )
            db.add(v)
        db.commit()

    from ..models.officer import Officer
    existing_officers = db.query(Officer).count()
    if existing_officers == 0:
        officers_data = [
            ("admin", "Admin User", "admin@urban.gov.in", "admin"),
            ("officer1", "Rajesh Kumar", "rajesh@urban.gov.in", "officer"),
            ("officer2", "Priya Singh", "priya@urban.gov.in", "officer"),
        ]
        for uname, name, email, role in officers_data:
            o = Officer(username=uname, name=name, email=email, role=role)
            db.add(o)
        db.commit()

    from ..models.fleet import FleetVehicle as FV
    vehicles = db.query(FV).all()

    potholes_data = [
        (17.3850, 78.4867, "high", 0.91, "VERIFIED"),
        (17.3880, 78.4900, "medium", 0.75, "PENDING_VERIFICATION"),
        (17.3910, 78.4830, "low", 0.60, "PENDING_VERIFICATION"),
        (17.3870, 78.4950, "high", 0.88, "WORK_STARTED"),
        (17.3820, 78.4880, "medium", 0.82, "FIXED"),
    ]
    existing_potholes = db.query(Pothole).count()
    if existing_potholes == 0:
        for i, (lat, lng, sev, conf, status) in enumerate(potholes_data):
            p = Pothole(
                pothole_id=generate_id("PH", i + 1),
                latitude=lat, longitude=lng, severity=sev,
                confidence=conf, status=status,
                detected_by_vehicle_id=vehicles[i % len(vehicles)].id if vehicles else None,
            )
            db.add(p)
        db.commit()

    violations_data = [
        ("NO_HELMET", "TS09AB1234", 17.3855, 78.4870, 0.94, "AI_VERIFIED"),
        ("NO_HELMET", "TS09CD5678", 17.3875, 78.4910, 0.67, "PENDING_OFFICER"),
        ("NO_HELMET", "TS09EF9012", 17.3900, 78.4850, 0.85, "AI_VERIFIED"),
        ("NO_HELMET", "TS09GH3456", 17.3860, 78.4930, 0.72, "PENDING_OFFICER"),
        ("NO_HELMET", "TS09IJ7890", 17.3830, 78.4890, 0.91, "AI_VERIFIED"),
    ]
    existing_violations = db.query(TrafficViolation).count()
    if existing_violations == 0:
        for i, (vtype, vnum, lat, lng, conf, vstatus) in enumerate(violations_data):
            v = TrafficViolation(
                violation_id=generate_id("TV", i + 1),
                violation_type=vtype, vehicle_number=vnum,
                timestamp=datetime.utcnow() - timedelta(hours=i),
                latitude=lat, longitude=lng, confidence=conf,
                status="AI_DETECTED" if vstatus == "AI_VERIFIED" else "PENDING_VERIFICATION",
                verification_status=vstatus,
                detected_by_vehicle_id=vehicles[i % len(vehicles)].id if vehicles else None,
            )
            db.add(v)
        db.commit()

    return {"detail": "Demo data seeded successfully"}
