from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from .database import init_db, SessionLocal
from .config import settings
from .routers import fleet, potholes, traffic, challans, map, notifications, demo, video, auth

app = FastAPI(
    title="Urban Intelligence Platform",
    description="Unified platform for fleet tracking, pothole detection, and traffic violation detection",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

upload_dir = os.path.join(settings.UPLOAD_DIR)
os.makedirs(upload_dir, exist_ok=True)
os.makedirs(os.path.join(upload_dir, "evidence"), exist_ok=True)
os.makedirs(os.path.join(upload_dir, "videos"), exist_ok=True)
os.makedirs(os.path.join(upload_dir, "frames"), exist_ok=True)

app.include_router(fleet.router)
app.include_router(potholes.router)
app.include_router(traffic.router)
app.include_router(challans.router)
app.include_router(map.router)
app.include_router(notifications.router)
app.include_router(demo.router)
app.include_router(video.router)
app.include_router(auth.router)

app.mount("/media", StaticFiles(directory=upload_dir), name="media")


@app.on_event("startup")
def startup():
    init_db()
    seed_if_empty()
    ensure_officer_passwords()
    normalize_legacy_video_evidence()


def seed_if_empty():
    from .models.fleet import FleetVehicle
    from .models.officer import Officer
    from .models.pothole import Pothole
    from .models.traffic_violation import TrafficViolation
    from datetime import datetime, timedelta, timezone
    from .utils.helpers import generate_id

    db = SessionLocal()
    try:
        if db.query(FleetVehicle).count() == 0:
            vehicles_data = [
                ("F-101", "TS09AB1234", "bus", "Route A - Central", 17.3850, 78.4867),
                ("F-102", "TS09CD5678", "bus", "Route B - East", 17.3880, 78.4900),
                ("F-103", "TS09EF9012", "bus", "Route C - West", 17.3910, 78.4830),
                ("F-104", "TS09GH3456", "van", "Route D - North", 17.3870, 78.4950),
                ("F-105", "TS09IJ7890", "car", "Route E - South", 17.3820, 78.4880),
            ]
            for fleet_id, vnum, vtype, route, lat, lng in vehicles_data:
                db.add(FleetVehicle(
                    fleet_id=fleet_id, vehicle_number=vnum, vehicle_type=vtype,
                    route_name=route, current_lat=lat, current_lng=lng,
                ))
            db.flush()

        if db.query(Officer).count() == 0:
            from .security import hash_password
            officers_data = [
                ("admin", "Admin User", "admin@urban.gov.in", "admin"),
                ("officer1", "Rajesh Kumar", "rajesh@urban.gov.in", "officer"),
                ("officer2", "Priya Singh", "priya@urban.gov.in", "officer"),
            ]
            for uname, name, email, role in officers_data:
                default = "admin123" if role == "admin" else "officer123"
                db.add(Officer(username=uname, name=name, email=email, role=role,
                               password_hash=hash_password(default)))
            db.commit()

        if settings.SEED_DEMO_DETECTIONS and db.query(Pothole).count() == 0 and db.query(FleetVehicle).count() > 0:
            vehicles = db.query(FleetVehicle).all()
            potholes_data = [
                (17.3850, 78.4867, "high", 0.91, "VERIFIED"),
                (17.3880, 78.4900, "medium", 0.75, "PENDING_VERIFICATION"),
                (17.3910, 78.4830, "low", 0.60, "PENDING_VERIFICATION"),
                (17.3870, 78.4950, "high", 0.88, "WORK_STARTED"),
                (17.3820, 78.4880, "medium", 0.82, "FIXED"),
            ]
            for i, (lat, lng, sev, conf, status) in enumerate(potholes_data):
                db.add(Pothole(
                    pothole_id=generate_id("PH", i + 1),
                    latitude=lat, longitude=lng, severity=sev,
                    confidence=conf, status=status,
                    detected_by_vehicle_id=vehicles[i % len(vehicles)].id,
                ))
            db.commit()

        if settings.SEED_DEMO_DETECTIONS and db.query(TrafficViolation).count() == 0 and db.query(FleetVehicle).count() > 0:
            vehicles = db.query(FleetVehicle).all()
            violations_data = [
                ("NO_HELMET", "TS09AB1234", 17.3855, 78.4870, 0.94, "AI_VERIFIED"),
                ("NO_HELMET", "TS09CD5678", 17.3875, 78.4910, 0.67, "PENDING_OFFICER"),
                ("NO_HELMET", "TS09EF9012", 17.3900, 78.4850, 0.85, "AI_VERIFIED"),
                ("NO_HELMET", "TS09GH3456", 17.3860, 78.4930, 0.72, "PENDING_OFFICER"),
                ("NO_HELMET", "TS09IJ7890", 17.3830, 78.4890, 0.91, "AI_VERIFIED"),
            ]
            for i, (vtype, vnum, lat, lng, conf, vstatus) in enumerate(violations_data):
                v = TrafficViolation(
                    violation_id=generate_id("TV", i + 1),
                    violation_type=vtype, vehicle_number=vnum,
                    timestamp=datetime.now(timezone.utc) - timedelta(hours=i + 1),
                    latitude=lat, longitude=lng, confidence=conf,
                    status="AI_DETECTED" if vstatus == "AI_VERIFIED" else "PENDING_VERIFICATION",
                    verification_status=vstatus,
                    detected_by_vehicle_id=vehicles[i % len(vehicles)].id,
                )
                db.add(v)
            db.commit()
    except Exception as e:
        print(f"Seeding error: {e}")
        db.rollback()
    finally:
        db.close()


def ensure_officer_passwords():
    from .models.officer import Officer
    from .security import hash_password

    db = SessionLocal()
    try:
        officers = db.query(Officer).all()
        for officer in officers:
            if not officer.password_hash:
                default = "admin123" if officer.role == "admin" else "officer123"
                officer.password_hash = hash_password(default)
        db.commit()
    except Exception as e:
        print(f"Password backfill error: {e}")
        db.rollback()
    finally:
        db.close()


def normalize_legacy_video_evidence():
    from .models.pothole import Pothole
    from .models.traffic_violation import TrafficViolation

    db = SessionLocal()
    try:
        fixed = 0
        for model in (TrafficViolation, Pothole):
            for rec in db.query(model).all():
                norm = (rec.evidence_video or "").replace("\\", "/")
                if "uploads/videos" in norm:
                    rec.evidence_video = f"/media/videos/{norm.rsplit('/', 1)[-1]}"
                    fixed += 1
        if fixed:
            db.commit()
            print(f"Normalized {fixed} legacy evidence_video path(s) to /media/videos/")
    except Exception as e:
        print(f"Evidence path normalization error: {e}")
        db.rollback()
    finally:
        db.close()


@app.get("/")
def root():
    return {"message": "Urban Intelligence Platform API", "version": "1.0.0"}


@app.get("/api/health")
def health():
    return {"status": "healthy", "ml_service": settings.ML_SERVICE_URL}
