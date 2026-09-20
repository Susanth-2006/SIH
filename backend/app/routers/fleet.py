from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database import get_db
from ..models.fleet import FleetVehicle, GPSPoint
from ..schemas.fleet import (
    FleetVehicleCreate, FleetVehicleResponse, FleetVehicleUpdate,
    FleetVehicleWithRoute, GPSPointCreate, GPSPointResponse
)
from ..services.notification_service import create_notification

router = APIRouter(prefix="/api/fleet", tags=["fleet"])


@router.post("/", response_model=FleetVehicleResponse)
def create_vehicle(vehicle: FleetVehicleCreate, db: Session = Depends(get_db)):
    existing = db.query(FleetVehicle).filter(FleetVehicle.fleet_id == vehicle.fleet_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Fleet ID already exists")
    db_vehicle = FleetVehicle(**vehicle.model_dump())
    db.add(db_vehicle)
    db.commit()
    db.refresh(db_vehicle)
    return db_vehicle


@router.get("/", response_model=List[FleetVehicleResponse])
def list_vehicles(
    skip: int = 0,
    limit: int = 100,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
):
    query = db.query(FleetVehicle)
    if is_active is not None:
        query = query.filter(FleetVehicle.is_active == is_active)
    return query.offset(skip).limit(limit).all()


@router.get("/{vehicle_id}", response_model=FleetVehicleWithRoute)
def get_vehicle(vehicle_id: int, db: Session = Depends(get_db)):
    vehicle = db.query(FleetVehicle).filter(FleetVehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return vehicle


@router.get("/{vehicle_id}/route", response_model=List[GPSPointResponse])
def get_vehicle_route(vehicle_id: int, limit: int = 500, db: Session = Depends(get_db)):
    vehicle = db.query(FleetVehicle).filter(FleetVehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    points = (
        db.query(GPSPoint)
        .filter(GPSPoint.vehicle_id == vehicle_id)
        .order_by(GPSPoint.timestamp.asc())
        .limit(limit)
        .all()
    )
    return points


@router.post("/{vehicle_id}/location", response_model=GPSPointResponse)
def update_location(vehicle_id: int, gps: GPSPointCreate, db: Session = Depends(get_db)):
    vehicle = db.query(FleetVehicle).filter(FleetVehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    vehicle.current_lat = gps.latitude
    vehicle.current_lng = gps.longitude
    vehicle.gps_status = "active"

    point = GPSPoint(
        vehicle_id=vehicle_id,
        latitude=gps.latitude,
        longitude=gps.longitude,
        speed=gps.speed,
        heading=gps.heading,
    )
    db.add(point)
    db.commit()
    db.refresh(point)
    return point


@router.patch("/{vehicle_id}", response_model=FleetVehicleResponse)
def update_vehicle(vehicle_id: int, update: FleetVehicleUpdate, db: Session = Depends(get_db)):
    vehicle = db.query(FleetVehicle).filter(FleetVehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    for key, value in update.model_dump(exclude_unset=True).items():
        setattr(vehicle, key, value)
    db.commit()
    db.refresh(vehicle)
    return vehicle


@router.delete("/{vehicle_id}")
def delete_vehicle(vehicle_id: int, db: Session = Depends(get_db)):
    vehicle = db.query(FleetVehicle).filter(FleetVehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    db.delete(vehicle)
    db.commit()
    return {"detail": "Vehicle deleted"}
