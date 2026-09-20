from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class MapMarker(BaseModel):
    id: str
    type: str
    latitude: float
    longitude: float
    title: str
    status: str
    confidence: Optional[float] = None
    details: Optional[dict] = None


class RoutePolyline(BaseModel):
    vehicle_id: str
    vehicle_number: str
    points: List[dict]
    color: str = "#4285F4"


class MapIncidentsResponse(BaseModel):
    fleet_markers: List[MapMarker]
    pothole_markers: List[MapMarker]
    violation_markers: List[MapMarker]
    routes: List[RoutePolyline]


class DashboardStats(BaseModel):
    fleet_active: int = 0
    fleet_offline: int = 0
    vehicles_tracked: int = 0
    potholes_total: int = 0
    potholes_pending: int = 0
    potholes_verified: int = 0
    potholes_work_started: int = 0
    potholes_work_finished: int = 0
    potholes_fixed: int = 0
    potholes_repair_failed: int = 0
    violations_total: int = 0
    violations_ai_verified: int = 0
    violations_pending: int = 0
    violations_officer_verified: int = 0
    violations_rejected: int = 0
    challans_generated: int = 0
    challans_paid: int = 0
    video_jobs: int = 0
    video_frames_processed: int = 0
    video_processing_completed: int = 0
