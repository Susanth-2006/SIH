from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ChallanCreate(BaseModel):
    violation_id: int


class ChallanResponse(BaseModel):
    id: int
    challan_id: str
    violation_id: int
    vehicle_number: Optional[str]
    violation_type: str
    fine_amount: float
    detection_timestamp: Optional[datetime]
    latitude: Optional[float]
    longitude: Optional[float]
    evidence_path: Optional[str]
    ai_confidence: Optional[float]
    verification_status: str
    challan_status: str
    officer_id: Optional[int]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChallanUpdate(BaseModel):
    challan_status: Optional[str] = None
    officer_id: Optional[int] = None
