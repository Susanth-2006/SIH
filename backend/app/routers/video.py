import os
import uuid
import json
import base64
import time
import threading
import httpx
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timezone, timedelta

from ..database import get_db
from ..config import settings
from ..models.video_job import VideoJob
from ..models.traffic_violation import TrafficViolation, TrafficEvidence
from ..models.pothole import Pothole
from ..models.fleet import FleetVehicle, GPSPoint
from ..utils.helpers import generate_id, calculate_fine, haversine_distance, next_id
from ..services.notification_service import create_notification
from ..services.challan_service import generate_challan

router = APIRouter(prefix="/api/video", tags=["video"])

DEFAULT_CENTER = (17.3850, 78.4867)
DEFAULT_ROUTE = ((17.3600, 78.4700), (17.4200, 78.5300))
API_BASE = "http://localhost:8000"
_ingest_lock = threading.Lock()
SAMPLE_VIDEO_EXTS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}


def _list_sample_videos():
    directory = settings.SAMPLE_VIDEO_DIR
    if not os.path.isdir(directory):
        return []
    entries = []
    for name in sorted(os.listdir(directory)):
        path = os.path.join(directory, name)
        if os.path.isfile(path) and os.path.splitext(name)[1].lower() in SAMPLE_VIDEO_EXTS:
            entries.append({
                "name": name,
                "size_bytes": os.path.getsize(path),
                "size_mb": round(os.path.getsize(path) / 1048576, 2),
            })
    return entries


def _resolve_sample_path(name: str):
    base = os.path.basename(name or "")
    if not base or os.path.splitext(base)[1].lower() not in SAMPLE_VIDEO_EXTS:
        raise HTTPException(status_code=400, detail="Invalid sample video name")
    path = os.path.join(settings.SAMPLE_VIDEO_DIR, base)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail=f"Sample video not found: {base}")
    return path


def _record_bus_route(db: Session, job: VideoJob):
    if not job.vehicle_id:
        return
    vehicle = db.query(FleetVehicle).filter(FleetVehicle.id == job.vehicle_id).first()
    if not vehicle:
        return
    start = (job.gps_start_lat if job.gps_start_lat is not None else DEFAULT_CENTER[0],
             job.gps_start_lng if job.gps_start_lng is not None else DEFAULT_CENTER[1])
    end = (job.gps_end_lat if job.gps_end_lat is not None else start[0],
           job.gps_end_lng if job.gps_end_lng is not None else start[1])
    duration = job.duration or 0
    points = 16
    base_time = job.created_at or datetime.now(timezone.utc)
    added = 0
    for i in range(points):
        frac = i / (points - 1)
        lat, lng = _interpolate_gps(start, end, frac)
        ts = base_time + timedelta(seconds=duration * frac)
        db.add(GPSPoint(vehicle_id=vehicle.id, latitude=round(lat, 6), longitude=round(lng, 6), timestamp=ts))
        added += 1
    vehicle.current_lat = end[0]
    vehicle.current_lng = end[1]
    vehicle.gps_status = "active"
    if not vehicle.route_name:
        vehicle.route_name = f"Bus route {vehicle.fleet_id}"
    db.commit()
    print(f"Recorded {added} route points for bus {vehicle.fleet_id} (job {job.job_id})")


def _vehicle_default_gps(db: Session, vehicle_id: Optional[int]):
    if vehicle_id:
        vehicle = db.query(FleetVehicle).filter(FleetVehicle.id == vehicle_id).first()
        if vehicle and vehicle.current_lat and vehicle.current_lng:
            return (vehicle.current_lat, vehicle.current_lng)
    return DEFAULT_CENTER


def _interpolate_gps(start, end, frac):
    frac = max(0.0, min(1.0, frac))
    lat = start[0] + (end[0] - start[0]) * frac
    lng = start[1] + (end[1] - start[1]) * frac
    return (lat, lng)


def _gps_at(job: VideoJob, ts_seconds: float):
    start_lat = job.gps_start_lat if job.gps_start_lat is not None else DEFAULT_CENTER[0]
    start_lng = job.gps_start_lng if job.gps_start_lng is not None else DEFAULT_CENTER[1]
    end_lat = job.gps_end_lat if job.gps_end_lat is not None else start_lat
    end_lng = job.gps_end_lng if job.gps_end_lng is not None else start_lng
    duration = job.duration or 0
    frac = ts_seconds / duration if duration > 0 else 0
    if start_lat == end_lat and start_lng == end_lng:
        r_start, r_end = DEFAULT_ROUTE
        return _interpolate_gps(r_start, r_end, frac)
    return _interpolate_gps((start_lat, start_lng), (end_lat, end_lng), frac)


def _video_evidence_url(job: VideoJob):
    filename = os.path.basename(job.video_path or "")
    if not filename:
        return None
    return f"/media/videos/{filename}"


def _save_evidence(job: VideoJob, det: dict):
    b64 = det.get("evidence_image")
    if not b64:
        return None
    try:
        data = b64.split(",", 1)[-1]
        img_bytes = base64.b64decode(data)
    except Exception as e:
        print(f"Evidence decode error: {e}")
        return None
    if len(img_bytes) < 100:
        return None
    d = os.path.join(settings.UPLOAD_DIR, "evidence", "video", job.job_id)
    os.makedirs(d, exist_ok=True)
    name = f"{det.get('type', 'det')}_{det.get('event_id', 'e')}_{int(time.time() * 1000) % 1000000}.jpg"
    rel = f"media/evidence/video/{job.job_id}/{name}"
    with open(os.path.join(d, name), "wb") as f:
        f.write(img_bytes)
    return f"/{rel}"


def _store_traffic_detection(db: Session, job: VideoJob, det: dict):
    vtype = det.get("violation_type", "OTHER")
    if vtype == "CORRECT":
        return None
    conf = float(det.get("confidence", 0.5))
    lat, lng = _gps_at(job, float(det.get("timestamp", 0)))
    vehicle_number = det.get("vehicle_number") or "UNKNOWN"
    evidence_rel = _save_evidence(job, det)

    violation = TrafficViolation(
        violation_id=next_id(db, TrafficViolation, "violation_id", "TV"),
        violation_type=vtype,
        vehicle_number=vehicle_number,
        timestamp=datetime.now(timezone.utc),
        latitude=round(lat, 6),
        longitude=round(lng, 6),
        confidence=conf,
        evidence_image=evidence_rel,
        evidence_video=_video_evidence_url(job),
        detection_details=json.dumps({
            "source": "video",
            "job_id": job.job_id,
            "frame_idx": det.get("frame_idx"),
            "timestamp": det.get("timestamp"),
            "first_timestamp": det.get("first_timestamp"),
            "frames_in_event": det.get("frames_in_event"),
            "bbox": det.get("bbox"),
            "sub_detections": det.get("sub_detections", []),
        }),
        detected_by_vehicle_id=job.vehicle_id,
        video_job_id=job.job_id,
    )

    if conf >= settings.CONFIDENCE_THRESHOLD:
        violation.status = "AI_DETECTED"
        violation.verification_status = "AI_VERIFIED"
    elif conf < settings.AUTO_REJECT_CONFIDENCE:
        violation.status = "REJECTED"
        violation.verification_status = "REJECTED"
    else:
        violation.status = "PENDING_VERIFICATION"
        violation.verification_status = "PENDING_OFFICER"

    violation.fine_amount = calculate_fine(vtype)
    db.add(violation)
    db.commit()
    db.refresh(violation)

    if conf >= settings.CONFIDENCE_THRESHOLD:
        generate_challan(db, violation.id)
        create_notification(
            db,
            title=f"Traffic Violation AI Verified: {violation.violation_id}",
            message=f"{vtype} detected from video with {conf*100:.1f}% confidence. Auto-verified. Challan generated.",
            notification_type="VIOLATION_AI_VERIFIED",
            related_entity_type="traffic_violation",
            related_entity_id=violation.id,
        )
    elif conf < settings.AUTO_REJECT_CONFIDENCE:
        create_notification(
            db,
            title=f"Traffic Violation Auto-Rejected: {violation.violation_id}",
            message=f"{vtype} detected from video with only {conf*100:.1f}% confidence. Below the auto-reject threshold, ignored.",
            notification_type="VIOLATION_REJECTED",
            related_entity_type="traffic_violation",
            related_entity_id=violation.id,
        )
    else:
        create_notification(
            db,
            title=f"Traffic Violation Requires Verification: {violation.violation_id}",
            message=f"{vtype} detected from video with {conf*100:.1f}% confidence. Requires officer verification.",
            notification_type="VIOLATION_VERIFICATION_NEEDED",
            related_entity_type="traffic_violation",
            related_entity_id=violation.id,
        )

    return violation


def _store_pothole_detection(db: Session, job: VideoJob, det: dict):
    conf = float(det.get("confidence", 0.5))

    lat, lng = _gps_at(job, float(det.get("timestamp", 0)))
    severity = det.get("severity") or ("medium" if conf >= settings.CONFIDENCE_THRESHOLD else "low")
    evidence_rel = _save_evidence(job, det)
    detail = json.dumps({
        "source": "video",
        "job_id": job.job_id,
        "frame_idx": det.get("frame_idx"),
        "timestamp": det.get("timestamp"),
        "first_timestamp": det.get("first_timestamp"),
        "frames_in_event": det.get("frames_in_event"),
        "bbox": det.get("bbox"),
        "severity": severity,
        "severity_note": "Estimated from bounding-box area ratio. Physical depth not measured.",
    })

    for existing in db.query(Pothole).all():
        if haversine_distance(lat, lng, existing.latitude, existing.longitude) >= settings.POOTHOLE_GPS_PROXIMITY_METERS:
            continue

        if existing.status in ["FIXED", "REPAIR_FAILED"]:
            existing.status = "REPAIR_VERIFICATION_PENDING"
            existing.video_job_id = job.job_id
            existing.updated_at = datetime.now(timezone.utc)
            if conf >= existing.confidence:
                existing.confidence = conf
            if evidence_rel:
                existing.evidence_image = evidence_rel
            db.commit()
            db.refresh(existing)
            create_notification(
                db,
                title=f"Pothole Re-Detected After Repair: {existing.pothole_id}",
                message=f"Pothole {existing.pothole_id} re-detected from video. Repair verification required at ({lat:.4f}, {lng:.4f}).",
                notification_type="POTHOLE_REPAIR_VERIFICATION_PENDING",
                related_entity_type="pothole",
                related_entity_id=existing.id,
            )
            return existing

        if existing.status == "REJECTED":
            existing.status = "PENDING_VERIFICATION"
            existing.video_job_id = job.job_id
            existing.updated_at = datetime.now(timezone.utc)
            if conf >= existing.confidence:
                existing.confidence = conf
            if evidence_rel:
                existing.evidence_image = evidence_rel
            db.commit()
            db.refresh(existing)
            create_notification(
                db,
                title=f"Pothole Re-Queued for Verification: {existing.pothole_id}",
                message=f"Previously rejected pothole {existing.pothole_id} re-detected from video.",
                notification_type="POTHOLE_VERIFICATION_NEEDED",
                related_entity_type="pothole",
                related_entity_id=existing.id,
            )
            return existing

        if conf >= existing.confidence:
            existing.confidence = conf
            existing.video_job_id = job.job_id
            existing.updated_at = datetime.now(timezone.utc)
            if evidence_rel:
                existing.evidence_image = evidence_rel
            db.commit()
            db.refresh(existing)
        else:
            existing.video_job_id = job.job_id
            db.commit()
            db.refresh(existing)
        return existing

    p = Pothole(
        pothole_id=next_id(db, Pothole, "pothole_id", "PH"),
        latitude=round(lat, 6),
        longitude=round(lng, 6),
        severity=severity,
        confidence=conf,
        evidence_image=evidence_rel,
        evidence_video=_video_evidence_url(job),
        detection_details=detail,
        detected_by_vehicle_id=job.vehicle_id,
        video_job_id=job.job_id,
        status="VERIFIED" if conf >= settings.CONFIDENCE_THRESHOLD else "PENDING_VERIFICATION",
    )
    db.add(p)
    db.commit()
    db.refresh(p)

    if conf >= settings.CONFIDENCE_THRESHOLD:
        create_notification(
            db,
            title=f"Pothole Detected: {p.pothole_id}",
            message=f"Pothole detected from video with {conf*100:.1f}% confidence at ({lat:.4f}, {lng:.4f}). Auto-verified.",
            notification_type="POTHOLE_DETECTED",
            related_entity_type="pothole",
            related_entity_id=p.id,
        )
    else:
        create_notification(
            db,
            title=f"Pothole Requires Verification: {p.pothole_id}",
            message=f"Pothole detected from video with {conf*100:.1f}% confidence. Requires officer verification.",
            notification_type="POTHOLE_VERIFICATION_NEEDED",
            related_entity_type="pothole",
            related_entity_id=p.id,
        )

    return p


def _get_ml_status(ml_job_id: str):
    try:
        with httpx.Client(timeout=15.0) as client:
            r = client.get(f"{settings.ML_SERVICE_URL}/process/video/status/{ml_job_id}")
            if r.status_code == 200:
                return r.json()
            if r.status_code == 404:
                return {"_not_found": True}
    except Exception as e:
        print(f"ML status check error: {e}")
    return None


def _mark_orphaned(db: Session, job: VideoJob):
    if job.status in ("submitted", "processing") and job.ml_job_id:
        job.status = "error"
        job.error = "Analysis job is no longer tracked by the ML service (service likely restarted). Please re-run."
        db.commit()
        print(f"Marked orphaned job {job.job_id} as error (ML job lost)")


def _ingest_ml_detections(db: Session, job: VideoJob):
    if job.status in ("completed", "error") or not job.ml_job_id:
        return
    ml = _get_ml_status(job.ml_job_id)
    if ml is None:
        return
    if ml.get("_not_found"):
        _mark_orphaned(db, job)
        return

    with _ingest_lock:
        db.refresh(job)
        if job.status == "completed":
            return
        ingested = set(json.loads(job.ingested_ids)) if job.ingested_ids else set()
        for det in ml.get("detections", []):
            eid = det.get("event_id")
            if not eid or eid in ingested:
                continue
            try:
                if det.get("type") == "traffic":
                    rec = _store_traffic_detection(db, job, det)
                else:
                    rec = _store_pothole_detection(db, job, det)
                ingested.add(eid)
            except Exception as e:
                print(f"Ingest error for event {eid}: {e}")
                db.rollback()
        job.ingested_ids = json.dumps(sorted(ingested))
        job.progress = float(ml.get("progress", job.progress or 0))
        job.frames_processed = int(ml.get("frames_processed", job.frames_processed or 0))
        job.total_frames = int(ml.get("total_frames", job.total_frames or 0))
        job.video_total_frames = int(ml.get("video_total_frames", job.video_total_frames or 0))
        job.duration = float(ml.get("duration") or job.duration or 0)
        job.traffic_detections = int(ml.get("traffic_events", job.traffic_detections or 0))
        job.pothole_detections = int(ml.get("pothole_events", job.pothole_detections or 0))
        if ml.get("status") == "completed":
            job.status = "completed"
            try:
                _record_bus_route(db, job)
            except Exception as e:
                print(f"Route recording error: {e}")
        elif ml.get("status") == "error":
            job.status = "error"
            job.error = ml.get("error")
        db.commit()


def _job_event_summary(db: Session, job: VideoJob):
    events = []
    for v in db.query(TrafficViolation).filter(TrafficViolation.video_job_id == job.job_id).all():
        events.append({
            "type": "traffic",
            "ref": v.violation_id,
            "violation_type": v.violation_type,
            "confidence": v.confidence,
            "timestamp": v.timestamp.isoformat() if v.timestamp else None,
            "latitude": v.latitude,
            "longitude": v.longitude,
            "vehicle_number": v.vehicle_number,
            "status": v.verification_status,
            "challan_status": v.challan_status,
            "evidence_url": (f"{API_BASE}{v.evidence_image}" if v.evidence_image else None),
        })
    for p in db.query(Pothole).filter(Pothole.video_job_id == job.job_id).all():
        events.append({
            "type": "pothole",
            "ref": p.pothole_id,
            "severity": p.severity,
            "confidence": p.confidence,
            "timestamp": p.created_at.isoformat() if p.created_at else None,
            "latitude": p.latitude,
            "longitude": p.longitude,
            "status": p.status,
            "evidence_url": (f"{API_BASE}{p.evidence_image}" if p.evidence_image else None),
        })
    return events


@router.get("/sample-videos")
def list_sample_videos():
    return {"videos": _list_sample_videos()}


@router.post("/process")
async def process_video(
    file: Optional[UploadFile] = File(None),
    sample_filename: Optional[str] = Form(None),
    vehicle_id: Optional[int] = Form(None),
    gps_start_lat: Optional[float] = Form(None),
    gps_start_lng: Optional[float] = Form(None),
    gps_end_lat: Optional[float] = Form(None),
    gps_end_lng: Optional[float] = Form(None),
    frame_interval: int = Form(20),
    min_confidence: float = Form(0.40),
    db: Session = Depends(get_db),
):
    if file is not None:
        ext = os.path.splitext(file.filename)[1] if file.filename else ".mp4"
        filename = f"video_{uuid.uuid4().hex[:8]}{ext}"
        src_label = file.filename or filename
        content = await file.read()
        _safe = os.path.join(settings.UPLOAD_DIR, "videos", filename)
        os.makedirs(os.path.dirname(_safe), exist_ok=True)
        with open(_safe, "wb") as f:
            f.write(content)
        filepath = _safe
    elif sample_filename:
        src_path = _resolve_sample_path(sample_filename)
        filename = f"video_{uuid.uuid4().hex[:8]}.mp4"
        src_label = os.path.basename(src_path)
        upload_dir = os.path.join(settings.UPLOAD_DIR, "videos")
        os.makedirs(upload_dir, exist_ok=True)
        filepath = os.path.join(upload_dir, filename)
        with open(src_path, "rb") as vf, open(filepath, "wb") as out:
            out.write(vf.read())
    else:
        raise HTTPException(status_code=400, detail="Provide a video file or a sample_filename")

    raw_start = (gps_start_lat, gps_start_lng) if gps_start_lat is not None and gps_start_lng is not None else None
    if raw_start is None:
        raw_start = _vehicle_default_gps(db, vehicle_id)
    raw_end = (gps_end_lat, gps_end_lng) if gps_end_lat is not None and gps_end_lng is not None else raw_start

    job = VideoJob(
        job_id=uuid.uuid4().hex[:12],
        filename=src_label,
        video_path=filepath,
        status="submitted",
        frame_interval=max(1, frame_interval),
        min_confidence=min_confidence,
        gps_start_lat=raw_start[0],
        gps_start_lng=raw_start[1],
        gps_end_lat=raw_end[0],
        gps_end_lng=raw_end[1],
        vehicle_id=vehicle_id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    try:
        with httpx.Client(timeout=120.0) as client:
            with open(filepath, "rb") as vf:
                r = client.post(
                    f"{settings.ML_SERVICE_URL}/process/video",
                    files={"file": (filename, vf, "video/mp4")},
                    data={
                        "frame_interval": str(max(1, frame_interval)),
                        "min_confidence": str(min_confidence),
                    },
                )
        if r.status_code != 200:
            raise RuntimeError(f"ML service returned {r.status_code}")
        ml = r.json()
        job.ml_job_id = ml.get("job_id")
        job.status = "processing"
    except Exception as e:
        job.status = "ml_unavailable"
        job.error = str(e)

    db.commit()
    db.refresh(job)

    return {
        "job_id": job.job_id,
        "status": job.status,
        "message": "Video analysis started." if job.status == "processing" else f"ML service unavailable: {job.error}",
    }


@router.get("/status/{job_id}")
def get_video_status(job_id: str, db: Session = Depends(get_db)):
    job = db.query(VideoJob).filter(VideoJob.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status in ("submitted", "processing", "ml_unavailable"):
        _ingest_ml_detections(db, job)

    return {
        "job_id": job.job_id,
        "status": job.status,
        "progress": job.progress,
        "frames_processed": job.frames_processed,
        "total_frames": job.total_frames,
        "video_total_frames": job.video_total_frames,
        "duration": job.duration,
        "traffic_detections": job.traffic_detections,
        "pothole_detections": job.pothole_detections,
        "gps_timeline": {
            "start": {"lat": job.gps_start_lat, "lng": job.gps_start_lng},
            "end": {"lat": job.gps_end_lat, "lng": job.gps_end_lng},
            "simulated": True,
        },
        "completed": job.status == "completed",
        "error": job.error,
        "detections": _job_event_summary(db, job),
    }


@router.get("/jobs")
def list_video_jobs(db: Session = Depends(get_db)):
    now = datetime.utcnow()
    for job in db.query(VideoJob).filter(VideoJob.status.in_(["submitted", "processing"])).all():
        updated = job.updated_at or job.created_at or now
        if (now - updated).total_seconds() < 90:
            continue
        try:
            _ingest_ml_detections(db, job)
        except Exception as e:
            print(f"Job adoption error {job.job_id}: {e}")
    jobs = db.query(VideoJob).order_by(VideoJob.created_at.desc()).limit(50).all()
    return [
        {
            "job_id": j.job_id,
            "filename": j.filename,
            "status": j.status,
            "progress": j.progress,
            "traffic_detections": j.traffic_detections,
            "pothole_detections": j.pothole_detections,
            "created_at": j.created_at.isoformat() if j.created_at else None,
        }
        for j in jobs
    ]


@router.post("/process-frames")
async def process_frames(
    file: UploadFile = File(...),
    detection_type: str = Form("traffic"),
    frame_interval: int = Form(20),
    gps_start_lat: Optional[float] = Form(None),
    gps_start_lng: Optional[float] = Form(None),
    gps_end_lat: Optional[float] = Form(None),
    gps_end_lng: Optional[float] = Form(None),
    vehicle_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
):
    ext = os.path.splitext(file.filename)[1] if file.filename else ".mp4"
    filename = f"frames_{uuid.uuid4().hex[:8]}{ext}"
    upload_dir = os.path.join(settings.UPLOAD_DIR, "videos")
    os.makedirs(upload_dir, exist_ok=True)
    filepath = os.path.join(upload_dir, filename)

    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)

    start_gps = (gps_start_lat, gps_start_lng) if gps_start_lat and gps_start_lng else _vehicle_default_gps(db, vehicle_id)
    end_gps = (gps_end_lat, gps_end_lng) if gps_end_lat and gps_end_lng else start_gps

    job = VideoJob(
        job_id=uuid.uuid4().hex[:12],
        filename=file.filename,
        video_path=filepath,
        status="processing",
        frame_interval=max(1, frame_interval),
        gps_start_lat=start_gps[0],
        gps_start_lng=start_gps[1],
        gps_end_lat=end_gps[0],
        gps_end_lng=end_gps[1],
        vehicle_id=vehicle_id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    total_frames = 0
    try:
        with httpx.Client(timeout=300.0) as client:
            with open(filepath, "rb") as vf:
                response = client.post(
                    f"{settings.ML_SERVICE_URL}/detect/{detection_type}/video",
                    files={"video": (filename, vf, "video/mp4")},
                    data={
                        "latitude": str(start_gps[0]),
                        "longitude": str(start_gps[1]),
                        "vehicle_id": str(vehicle_id) if vehicle_id else "",
                        "frame_interval": str(frame_interval),
                    },
                )
        if response.status_code != 200:
            raise RuntimeError(f"ML service returned {response.status_code}")
        ml = response.json()
        detections = ml.get("detections", [])
        frame_count = ml.get("frame_count", 0)
        total_frames = frame_count * max(frame_interval, 1)
        job.duration = (total_frames / 25.0) if total_frames else 0

        created = []
        for det in detections:
            det.setdefault("timestamp", 0)
            if detection_type == "pothole":
                rec = _store_pothole_detection(db, job, det)
            else:
                rec = _store_traffic_detection(db, job, det)
            if rec is not None:
                created.append(getattr(rec, "violation_id", None) or getattr(rec, "pothole_id", None))
        job.status = "completed"
        db.commit()

        return {
            "status": "processed",
            "gps_timeline": {
                "start": {"lat": start_gps[0], "lng": start_gps[1]},
                "end": {"lat": end_gps[0], "lng": end_gps[1]},
            },
            "created": created,
            "message": f"Processed {len(detections)} detections across {frame_count} frames.",
        }
    except Exception as e:
        job.status = "ml_unavailable"
        job.error = str(e)
        db.commit()
        return {
            "status": "ml_service_unavailable",
            "message": f"ML service not available: {str(e)}. No records created.",
            "gps_timeline": {
                "start": {"lat": start_gps[0], "lng": start_gps[1]},
                "end": {"lat": end_gps[0], "lng": end_gps[1]},
            },
            "created": [],
        }