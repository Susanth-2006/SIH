from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class TrafficViolationCreate(BaseModel):
    violation_type: str
    vehicle_number: Optional[str] = None
    timestamp: Optional[datetime] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    confidence: float
    evidence_image: Optional[str] = None
    evidence_video: Optional[str] = None
    detection_details: Optional[str] = None
    detected_by_vehicle_id: Optional[int] = None


class TrafficViolationResponse(BaseModel):
    id: int
    violation_id: str
    violation_type: str
    vehicle_number: Optional[str]
    timestamp: Optional[datetime]
    latitude: Optional[float]
    longitude: Optional[float]
    confidence: float
    evidence_image: Optional[str]
    evidence_video: Optional[str]
    detection_details: Optional[str]
    detected_by_vehicle_id: Optional[int]
    status: str
    verification_status: str
    fine_amount: float
    challan_status: str
    verified_by_officer_id: Optional[int]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TrafficViolationVerify(BaseModel):
    officer_id: Optional[int] = None
    notes: Optional[str] = None


class TrafficEvidenceCreate(BaseModel):
    evidence_type: str
    file_path: str
    timestamp: Optional[datetime] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    vehicle_number: Optional[str] = None
    violation_type: Optional[str] = None
    confidence: Optional[float] = None
    ocr_result: Optional[str] = None


class TrafficEvidenceResponse(BaseModel):
    id: int
    violation_id: int
    evidence_type: str
    file_path: str
    timestamp: Optional[datetime]
    latitude: Optional[float]
    longitude: Optional[float]
    vehicle_number: Optional[str]
    violation_type: Optional[str]
    confidence: Optional[float]
    ocr_result: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class TrafficViolationWithEvidence(TrafficViolationResponse):
    evidence_records: List[TrafficEvidenceResponse] = []
