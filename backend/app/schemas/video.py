from typing import Optional, Any
from pydantic import BaseModel


class VideoProcessResponse(BaseModel):
    job_id: str
    status: str
    message: str


class VideoEvent(BaseModel):
    event_id: str
    type: str
    confidence: float
    timestamp: Optional[float] = None
    severity: Optional[str] = None
    violation_type: Optional[str] = None
    vehicle_number: Optional[str] = None
    evidence_url: Optional[str] = None


class VideoJobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: float
    frames_processed: int
    total_frames: int
    video_total_frames: int
    duration: float
    traffic_detections: int
    pothole_detections: int
    completed: bool
    error: Optional[str] = None
    detections: list = []


class VideoJobListResponse(BaseModel):
    job_id: str
    filename: Optional[str] = None
    status: str
    progress: float
    traffic_detections: int
    pothole_detections: int
    created_at: Any = None