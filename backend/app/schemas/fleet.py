from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class FleetVehicleBase(BaseModel):
    fleet_id: str
    vehicle_number: str
    vehicle_type: str = "bus"
    route_name: Optional[str] = None


class FleetVehicleCreate(FleetVehicleBase):
    pass


class FleetVehicleUpdate(BaseModel):
    current_lat: Optional[float] = None
    current_lng: Optional[float] = None
    camera_status: Optional[str] = None
    gps_status: Optional[str] = None
    is_active: Optional[bool] = None
    route_name: Optional[str] = None


class GPSPointCreate(BaseModel):
    latitude: float
    longitude: float
    speed: Optional[float] = None
    heading: Optional[float] = None


class GPSPointResponse(BaseModel):
    id: int
    latitude: float
    longitude: float
    speed: Optional[float]
    heading: Optional[float]
    timestamp: datetime

    class Config:
        from_attributes = True


class FleetVehicleResponse(FleetVehicleBase):
    id: int
    vehicle_type: str
    current_lat: Optional[float]
    current_lng: Optional[float]
    camera_status: str
    gps_status: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FleetVehicleWithRoute(FleetVehicleResponse):
    gps_points: List[GPSPointResponse] = []
