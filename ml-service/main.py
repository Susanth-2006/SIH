import os
import sys
import uuid
import cv2
import numpy as np
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from pydantic import BaseModel

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from traffic_detector import TrafficDetector
from pothole_detector import PotholeDetector
from video_processor import VideoProcessor

app = FastAPI(title="ML Detection Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
TMP_DIR = os.path.join(os.path.dirname(__file__), "tmp")
os.makedirs(TMP_DIR, exist_ok=True)

traffic_detector = TrafficDetector()
pothole_detector = PotholeDetector()
video_processor = VideoProcessor(traffic_detector, pothole_detector, ocr_token=os.getenv("PLATERECOGNIZER_TOKEN", ""))

PLATFORM_DIR = os.path.join(os.path.dirname(__file__), "..")
CONFIDENCE_THRESHOLD = 0.25
IOU_THRESHOLD = 0.45
IMG_SIZE = 448


class DetectionResult(BaseModel):
    violation_type: str
    confidence: float
    vehicle_number: Optional[str] = None
    evidence_image: Optional[str] = None
    detection_details: Optional[str] = None


def extract_frames(video_path: str, interval: int = 20):
    cap = cv2.VideoCapture(video_path)
    frames = []
    frame_idx = 0
    fps = cap.get(cv2.CAP_PROP_FPS) or 30

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        if frame_idx % interval == 0:
            timestamp = frame_idx / fps
            frames.append((frame, timestamp, frame_idx))
        frame_idx += 1

    cap.release()
    return frames


def _clean_detection(d):
    safe = {}
    for k, v in d.items():
        if k == "lp_image":
            continue
        safe[k] = v
    return safe


@app.on_event("startup")
def startup():
    traffic_detector.load()
    pothole_detector.load()


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "traffic_model_loaded": traffic_detector.loaded,
        "traffic_mode": "yolo" if traffic_detector.loaded else "mock",
        "pothole_model_loaded": pothole_detector.loaded,
        "pothole_mode": "yolo" if pothole_detector.loaded else "cv-heuristic",
        "device": str(traffic_detector.device) if traffic_detector.device else str(pothole_detector.device or "none"),
    }


@app.post("/detect/traffic")
async def detect_traffic(frame: UploadFile = File(...)):
    contents = await frame.read()
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        return {"error": "Invalid image", "detections": []}

    detections = traffic_detector.detect(img)
    cleaned = [_clean_detection(d) for d in detections]
    return {
        "detections": cleaned,
        "frame_count": 1,
        "processed": True,
        "mode": "real" if traffic_detector.loaded else "mock",
    }


@app.post("/detect/pothole")
async def detect_pothole(frame: UploadFile = File(...)):
    contents = await frame.read()
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        return {"error": "Invalid image", "detections": []}

    detections = pothole_detector.detect(img)
    return {
        "detections": detections,
        "frame_count": 1,
        "processed": True,
        "mode": "real" if pothole_detector.loaded else "cv-heuristic",
    }


def _video_path(prefix):
    os.makedirs(TMP_DIR, exist_ok=True)
    return os.path.join(TMP_DIR, f"{prefix}_{uuid.uuid4().hex[:8]}.mp4")


@app.post("/detect/traffic/video")
async def detect_traffic_video(
    video: UploadFile = File(...),
    latitude: Optional[str] = Form(None),
    longitude: Optional[str] = Form(None),
    vehicle_id: Optional[str] = Form(None),
    frame_interval: int = Form(20),
):
    temp_path = _video_path("video")
    contents = await video.read()
    with open(temp_path, "wb") as f:
        f.write(contents)

    frames = extract_frames(temp_path, interval=frame_interval)
    all_detections = []

    for frame_img, timestamp, frame_idx in frames:
        detections = traffic_detector.detect(frame_img)
        for d in detections:
            d = _clean_detection(d)
            d["frame_idx"] = frame_idx
            d["timestamp"] = round(timestamp, 2)
            all_detections.append(d)

    try:
        os.remove(temp_path)
    except Exception:
        pass

    return {
        "detections": all_detections,
        "frame_count": len(frames),
        "total_violations": len(all_detections),
        "processed": True,
    }


@app.post("/detect/pothole/video")
async def detect_pothole_video(
    video: UploadFile = File(...),
    latitude: Optional[str] = Form(None),
    longitude: Optional[str] = Form(None),
    vehicle_id: Optional[str] = Form(None),
    frame_interval: int = Form(20),
):
    temp_path = _video_path("pothole_video")
    contents = await video.read()
    with open(temp_path, "wb") as f:
        f.write(contents)

    frames = extract_frames(temp_path, interval=frame_interval)
    all_detections = []
    for i, (frame_img, timestamp, frame_idx) in enumerate(frames):
        detections = pothole_detector.detect(frame_img, frame_index=frame_idx)
        for d in detections:
            d["frame_idx"] = frame_idx
            d["timestamp"] = round(timestamp, 2)
            all_detections.append(d)

    try:
        os.remove(temp_path)
    except Exception:
        pass

    return {
        "detections": all_detections,
        "frame_count": len(frames),
        "total_potholes": len(all_detections),
        "processed": True,
    }


@app.post("/process/video")
async def process_video(
    file: UploadFile = File(...),
    frame_interval: int = Form(20),
    min_confidence: float = Form(0.40),
):
    temp_path = _video_path("job_video")
    contents = await file.read()
    with open(temp_path, "wb") as f:
        f.write(contents)

    job_id = video_processor.start_job(
        temp_path,
        file.filename or "video.mp4",
        frame_interval=frame_interval,
        min_confidence=min_confidence,
    )
    return {
        "job_id": job_id,
        "status": "running",
        "message": "Video analysis started. Both traffic and pothole detection will run.",
        "progress": 0,
    }


@app.get("/process/video/status/{job_id}")
def process_video_status(job_id: str):
    status = video_processor.get_status(job_id)
    if status is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Job not found")
    return status


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)