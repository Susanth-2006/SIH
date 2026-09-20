from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from datetime import datetime, timezone
from ..database import Base


class VideoJob(Base):
    __tablename__ = "video_jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(40), unique=True, index=True, nullable=False)
    filename = Column(String(255), nullable=True)
    video_path = Column(String(500), nullable=True)
    ml_job_id = Column(String(40), nullable=True)
    status = Column(String(30), default="submitted")
    progress = Column(Float, default=0.0)
    total_frames = Column(Integer, default=0)
    frames_processed = Column(Integer, default=0)
    video_total_frames = Column(Integer, default=0)
    duration = Column(Float, default=0.0)
    frame_interval = Column(Integer, default=20)
    min_confidence = Column(Float, default=0.40)
    gps_start_lat = Column(Float, nullable=True)
    gps_start_lng = Column(Float, nullable=True)
    gps_end_lat = Column(Float, nullable=True)
    gps_end_lng = Column(Float, nullable=True)
    vehicle_id = Column(Integer, nullable=True)
    traffic_detections = Column(Integer, default=0)
    pothole_detections = Column(Integer, default=0)
    ingested_ids = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))