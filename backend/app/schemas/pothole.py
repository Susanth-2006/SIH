from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class PotholeCreate(BaseModel):
    latitude: float
    longitude: float
    severity: str = "medium"
    confidence: float
    detected_by_vehicle_id: Optional[int] = None
    evidence_image: Optional[str] = None
    evidence_video: Optional[str] = None
    detection_details: Optional[str] = None


class PotholeResponse(BaseModel):
    id: int
    pothole_id: str
    latitude: float
    longitude: float
    severity: str
    confidence: float
    status: str
    detected_by_vehicle_id: Optional[int]
    evidence_image: Optional[str]
    evidence_video: Optional[str]
    detection_details: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PotholeVerify(BaseModel):
    action: str
    officer_id: Optional[int] = None
    notes: Optional[str] = None


class PotholeWorkUpdate(BaseModel):
    officer_id: Optional[int] = None
    notes: Optional[str] = None


class PotholeVerificationResponse(BaseModel):
    id: int
    pothole_id: int
    officer_id: Optional[int]
    action: str
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
