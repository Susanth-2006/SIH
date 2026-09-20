import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["DATABASE_URL"] = "sqlite:///./test_urban_intelligence.db"
os.environ["DEBUG"] = "false"
os.environ["ML_SERVICE_URL"] = "http://localhost:59999"

for _f in ("test_urban_intelligence.db",):
    try:
        os.remove(_f)
    except OSError:
        pass

from fastapi.testclient import TestClient
from app.main import app

POTHOLE_HIGH_CONF = {
    "latitude": 17.3850,
    "longitude": 78.4867,
    "severity": "high",
    "confidence": 0.91,
    "detected_by_vehicle_id": 1,
    "detection_details": "test detection",
}

POTHOLE_LOW_CONF = {
    "latitude": 17.3900,
    "longitude": 78.4900,
    "severity": "medium",
    "confidence": 0.65,
    "detected_by_vehicle_id": 1,
}

VIOLATION_HIGH_CONF = {
    "violation_type": "NO_HELMET",
    "vehicle_number": "TS09XX0001",
    "latitude": 17.3860,
    "longitude": 78.4875,
    "confidence": 0.94,
    "detected_by_vehicle_id": 1,
}

VIOLATION_LOW_CONF = {
    "violation_type": "NO_HELMET",
    "vehicle_number": "TS09XX0002",
    "latitude": 17.3870,
    "longitude": 78.4880,
    "confidence": 0.67,
    "detected_by_vehicle_id": 1,
}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        assert c.get("/api/health").status_code == 200
        for i, vid in enumerate(["F-201", "F-202"]):
            c.post("/api/fleet/", json={
                "fleet_id": vid,
                "vehicle_number": f"TS09N{1000+i}",
                "vehicle_type": "bus",
                "route_name": f"Test Route {i}",
            })
        yield c


# ============= POTHOLE TESTS =============

def test_high_confidence_pothole_auto_verified(client):
    r = client.post("/api/potholes/detect", json=POTHOLE_HIGH_CONF)
    assert r.status_code == 200
    data = r.json()
    assert data["confidence"] == 0.91
    assert data["status"] == "VERIFIED"
    assert data["pothole_id"].startswith("PH")


def test_low_confidence_pothole_pending_verification(client):
    r = client.post("/api/potholes/detect", json=POTHOLE_LOW_CONF)
    assert r.status_code == 200
    data = r.json()
    assert data["confidence"] == 0.65
    assert data["status"] == "PENDING_VERIFICATION"


def test_pothole_officer_verification(client):
    r = client.post("/api/potholes/detect", json=POTHOLE_LOW_CONF)
    assert r.status_code == 200
    pothole = r.json()

    r = client.post(f"/api/potholes/{pothole['id']}/verify", json={"action": "VERIFIED", "officer_id": 1})
    assert r.status_code == 200
    assert r.json()["status"] == "VERIFIED"


def test_pothole_rejection(client):
    low = dict(POTHOLE_LOW_CONF)
    low["latitude"] = 17.3920
    low["longitude"] = 78.4920
    r = client.post("/api/potholes/detect", json=low)
    pothole = r.json()

    r = client.post(f"/api/potholes/{pothole['id']}/verify", json={"action": "REJECTED", "officer_id": 1})
    assert r.status_code == 200
    assert r.json()["status"] == "REJECTED"


def test_pothole_work_started(client):
    r = client.post("/api/potholes/detect", json=POTHOLE_HIGH_CONF)
    pothole = r.json()

    r = client.post(f"/api/potholes/{pothole['id']}/start-work", json={"officer_id": 1})
    assert r.status_code == 200
    assert r.json()["status"] == "WORK_STARTED"


def test_pothole_work_started_requires_verified(client):
    low = dict(POTHOLE_LOW_CONF)
    low["latitude"] = 17.3930
    low["longitude"] = 78.4930
    r = client.post("/api/potholes/detect", json=low)
    pothole = r.json()
    assert pothole["status"] == "PENDING_VERIFICATION"

    r = client.post(f"/api/potholes/{pothole['id']}/start-work", json={"officer_id": 1})
    assert r.status_code == 400


def test_pothole_finish_work(client):
    r = client.post("/api/potholes/detect", json=POTHOLE_HIGH_CONF)
    pothole = r.json()
    client.post(f"/api/potholes/{pothole['id']}/start-work", json={"officer_id": 1})

    r = client.post(f"/api/potholes/{pothole['id']}/finish-work", json={"officer_id": 1})
    assert r.status_code == 200
    assert r.json()["status"] == "WORK_FINISHED"


def test_pothole_repair_verification(client):
    r = client.post("/api/potholes/detect", json=POTHOLE_HIGH_CONF)
    pothole = r.json()
    client.post(f"/api/potholes/{pothole['id']}/start-work", json={"officer_id": 1})
    client.post(f"/api/potholes/{pothole['id']}/finish-work", json={"officer_id": 1})

    r = client.post(f"/api/potholes/{pothole['id']}/repair-verify", json={"action": "REPAIR_VERIFIED", "officer_id": 1})
    assert r.status_code == 200
    assert r.json()["status"] == "FIXED"


def test_duplicate_pothole_detection_returns_existing(client):
    r1 = client.post("/api/potholes/detect", json=POTHOLE_HIGH_CONF)
    first = r1.json()

    dup = dict(POTHOLE_HIGH_CONF)
    dup["confidence"] = 0.88
    r2 = client.post("/api/potholes/detect", json=dup)
    second = r2.json()

    assert second["id"] == first["id"]
    assert second["pothole_id"] == first["pothole_id"]


def test_duplicate_pothole_ignores_fixed(client):
    r1 = client.post("/api/potholes/detect", json=POTHOLE_HIGH_CONF)
    first = r1.json()
    client.post(f"/api/potholes/{first['id']}/start-work", json={"officer_id": 1})
    client.post(f"/api/potholes/{first['id']}/finish-work", json={"officer_id": 1})
    client.post(f"/api/potholes/{first['id']}/repair-verify", json={"action": "REPAIR_VERIFIED", "officer_id": 1})

    assert client.get(f"/api/potholes/{first['id']}").json()["status"] == "FIXED"

    dup = dict(POTHOLE_HIGH_CONF)
    dup["latitude"] = first["latitude"] + 0.0003
    dup["longitude"] = first["longitude"]
    r2 = client.post("/api/potholes/detect", json=dup)
    assert r2.status_code == 200


def test_fixed_pothole_redetection_triggers_repair_verification(client):
    r = client.post("/api/potholes/detect", json=POTHOLE_HIGH_CONF)
    pothole = r.json()
    client.post(f"/api/potholes/{pothole['id']}/start-work", json={"officer_id": 1})
    client.post(f"/api/potholes/{pothole['id']}/finish-work", json={"officer_id": 1})
    client.post(f"/api/potholes/{pothole['id']}/repair-verify", json={"action": "REPAIR_VERIFIED", "officer_id": 1})
    assert client.get(f"/api/potholes/{pothole['id']}").json()["status"] == "FIXED"

    r = client.post("/api/potholes/detect", json=POTHOLE_HIGH_CONF)
    assert r.status_code == 200
    assert r.json()["id"] == pothole["id"]
    assert r.json()["status"] == "REPAIR_VERIFICATION_PENDING"


def test_rejected_pothole_redetection_requeues_verification(client):
    low = dict(POTHOLE_LOW_CONF)
    low["latitude"] = 17.3940
    low["longitude"] = 78.4940
    r = client.post("/api/potholes/detect", json=low)
    pothole = r.json()
    client.post(f"/api/potholes/{pothole['id']}/verify", json={"action": "REJECTED", "officer_id": 1})
    assert client.get(f"/api/potholes/{pothole['id']}").json()["status"] == "REJECTED"

    r = client.post("/api/potholes/detect", json=low)
    assert r.status_code == 200
    assert r.json()["id"] == pothole["id"]
    assert r.json()["status"] == "PENDING_VERIFICATION"


# ============= TRAFFIC VIOLATION TESTS =============

def test_high_confidence_violation_ai_verified(client):
    r = client.post("/api/traffic/detect", json=VIOLATION_HIGH_CONF)
    assert r.status_code == 200
    data = r.json()
    assert data["verification_status"] == "AI_VERIFIED"
    assert data["status"] == "AI_DETECTED"
    assert data["challan_status"] == "GENERATED"
    assert data["fine_amount"] == 500
    assert data["violation_id"].startswith("TV")


def test_low_confidence_violation_pending(client):
    r = client.post("/api/traffic/detect", json=VIOLATION_LOW_CONF)
    assert r.status_code == 200
    data = r.json()
    assert data["verification_status"] == "PENDING_OFFICER"
    assert data["status"] == "PENDING_VERIFICATION"
    assert data["challan_status"] == "NOT_GENERATED"


def test_officer_verification_generates_challan(client):
    r = client.post("/api/traffic/detect", json=VIOLATION_LOW_CONF)
    violation = r.json()

    r = client.post(f"/api/traffic/violations/{violation['id']}/verify", json={"officer_id": 1})
    assert r.status_code == 200
    data = r.json()
    assert data["verification_status"] == "OFFICER_VERIFIED"
    assert data["challan_status"] == "GENERATED"
    assert data["fine_amount"] == 500


def test_officer_rejection(client):
    r = client.post("/api/traffic/detect", json=VIOLATION_LOW_CONF)
    violation = r.json()

    r = client.post(f"/api/traffic/violations/{violation['id']}/reject", json={"officer_id": 1})
    assert r.status_code == 200
    data = r.json()
    assert data["verification_status"] == "REJECTED"
    assert data["status"] == "REJECTED"


def test_multiple_violations(client):
    types = ["NO_HELMET"]
    for i, vtype in enumerate(types):
        v = dict(VIOLATION_HIGH_CONF)
        v["violation_type"] = vtype
        v["latitude"] = 17.3860 + i * 0.001
        v["longitude"] = 78.4875 + i * 0.001
        v["vehicle_number"] = f"TS09XX{i}00"
        r = client.post("/api/traffic/detect", json=v)
        assert r.status_code == 200
        assert r.json()["violation_type"] == vtype


def test_number_plate_ocr_failure(client):
    v = dict(VIOLATION_HIGH_CONF)
    v["vehicle_number"] = None
    v["latitude"] = 17.4000
    v["longitude"] = 78.5000
    v["detection_details"] = "Number_plate OCR failed: low confidence"
    r = client.post("/api/traffic/detect", json=v)
    assert r.status_code == 200
    data = r.json()
    assert data["vehicle_number"] is None
    assert "Number_plate" in (data["detection_details"] or "")


def test_missing_gps(client):
    v = dict(VIOLATION_HIGH_CONF)
    v["latitude"] = None
    v["longitude"] = None
    v["vehicle_number"] = "TS09XX9999"
    r = client.post("/api/traffic/detect", json=v)
    assert r.status_code == 200
    assert r.json()["latitude"] is None


def test_invalid_detection_high_confidence_auto_challan(client):
    v = dict(VIOLATION_HIGH_CONF)
    v["violation_type"] = "WRONG_ROUTE"
    r = client.post("/api/traffic/detect", json=v)
    assert r.status_code == 200
    data = r.json()
    assert data["verification_status"] == "AI_VERIFIED"
    assert data["fine_amount"] == 1000


# ============= CHALLAN TESTS =============

def test_challan_generated_and_listed(client):
    r = client.post("/api/traffic/detect", json=VIOLATION_HIGH_CONF)
    violation = r.json()

    r = client.get("/api/challans/")
    assert r.status_code == 200
    challans = r.json()
    assert any(c["violation_id"] == violation["id"] for c in challans)


def test_challan_status_update(client):
    r = client.post("/api/traffic/detect", json=VIOLATION_HIGH_CONF)
    violation = r.json()

    challan = client.get("/api/challans/").json()
    c = [x for x in challan if x["violation_id"] == violation["id"]][0]

    r = client.patch(f"/api/challans/{c['id']}", json={"challan_status": "PAID"})
    assert r.status_code == 200
    assert r.json()["challan_status"] == "PAID"


# ============= MAP TESTS =============

def test_map_incidents(client):
    r = client.get("/api/map/incidents")
    assert r.status_code == 200
    data = r.json()
    assert "fleet_markers" in data
    assert "pothole_markers" in data
    assert "violation_markers" in data
    assert "routes" in data


def test_map_fleet_marker(client):
    r = client.get("/api/map/incidents")
    data = r.json()
    assert any(m["type"] == "fleet" for m in data["fleet_markers"])


def test_map_pothole_marker(client):
    client.post("/api/potholes/detect", json=POTHOLE_HIGH_CONF)
    r = client.get("/api/map/incidents")
    data = r.json()
    assert any(m["type"] == "pothole" for m in data["pothole_markers"])


def test_map_violation_marker(client):
    client.post("/api/traffic/detect", json=VIOLATION_HIGH_CONF)
    r = client.get("/api/map/incidents")
    data = r.json()
    assert any(m["type"] == "traffic_violation" for m in data["violation_markers"])


def test_map_route_rendering(client):
    client.post("/api/fleet/1/location", json={"latitude": 17.3850, "longitude": 78.4867})
    client.post("/api/fleet/1/location", json={"latitude": 17.3860, "longitude": 78.4877})
    r = client.get("/api/map/incidents")
    data = r.json()
    assert len(data["routes"]) >= 1
    assert len(data["routes"][0]["points"]) >= 1


# ============= FLEET TESTS =============

def test_fleet_list(client):
    r = client.get("/api/fleet/")
    assert r.status_code == 200
    assert len(r.json()) >= 2


def test_fleet_gps_update(client):
    r = client.post("/api/fleet/1/location", json={"latitude": 17.3880, "longitude": 78.4900, "speed": 40.5})
    assert r.status_code == 200
    data = r.json()
    assert data["latitude"] == 17.3880
    assert data["longitude"] == 78.4900
    assert data["speed"] == 40.5


def test_fleet_route_history(client):
    r = client.get("/api/fleet/1/route")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# ============= NOTIFICATION TESTS =============

def test_notifications_created(client):
    r = client.get("/api/notifications/")
    assert r.status_code == 200
    notifications = r.json()
    assert len(notifications) > 0


def test_notification_mark_read(client):
    r = client.get("/api/notifications/")
    notifications = r.json()
    if notifications:
        nid = notifications[0]["id"]
        r = client.patch(f"/api/notifications/{nid}/read")
        assert r.status_code == 200
        assert r.json()["is_read"] is True


# ============= DASHBOARD TESTS =============

def test_dashboard_statistics(client):
    r = client.get("/api/dashboard/statistics")
    assert r.status_code == 200
    data = r.json()
    assert "fleet_active" in data
    assert "potholes_total" in data
    assert "violations_total" in data
    assert "challans_generated" in data


# ============= DEMO TESTS =============

def test_demo_seed(client):
    r = client.post("/api/demo/seed")
    assert r.status_code == 200
    assert "detail" in r.json()


def test_demo_simulate_fleet(client):
    r = client.post("/api/demo/simulate-fleet", json={"vehicle_id": 1})
    assert r.status_code == 200
    assert "points_created" in r.json()


def test_demo_add_pothole(client):
    r = client.post("/api/demo/add-pothole", json={"confidence": 0.85})
    assert r.status_code == 200
    assert r.json()["status"] == "VERIFIED"


def test_demo_add_violation(client):
    r = client.post("/api/demo/add-violation", json={"confidence": 0.92})
    assert r.status_code == 200
    assert r.json()["verification_status"] == "AI_VERIFIED"


# ============= VIDEO PIPELINE TESTS =============

def _make_video(tmp_path):
    import cv2
    import numpy as np
    p = os.path.join(tmp_path, "sample.mp4")
    vw = cv2.VideoWriter(p, cv2.VideoWriter_fourcc(*"mp4v"), 15, (320, 240))
    for _ in range(30):
        vw.write(np.zeros((240, 320, 3), dtype=np.uint8))
    vw.release()
    return p


@pytest.fixture(scope="module")
def sample_video():
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        yield _make_video(td)


def test_video_process_creates_job(client, sample_video):
    with open(sample_video, "rb") as vf:
        r = client.post(
            "/api/video/process",
            data={
                "gps_start_lat": "17.3800",
                "gps_start_lng": "78.4850",
                "gps_end_lat": "17.4000",
                "gps_end_lng": "78.4980",
                "vehicle_id": "1",
                "frame_interval": "5",
            },
            files={"file": ("sample.mp4", vf, "video/mp4")},
        )
    assert r.status_code == 200
    data = r.json()
    assert "job_id" in data
    assert data["status"] in ("processing", "ml_unavailable")


def test_video_status_returns_job(client, sample_video):
    with open(sample_video, "rb") as vf:
        job = client.post(
            "/api/video/process",
            data={"gps_lat": "17.3900", "gps_lng": "78.4900", "vehicle_id": "1"},
            files={"file": ("sample.mp4", vf, "video/mp4")},
        ).json()

    r = client.get(f"/api/video/status/{job['job_id']}")
    assert r.status_code == 200
    data = r.json()
    assert data["job_id"] == job["job_id"]
    assert data["status"] == "ml_unavailable"
    assert "progress" in data
    assert "traffic_detections" in data
    assert "pothole_detections" in data
    assert data["completed"] is False
    assert data["gps_timeline"]["simulated"] is True


def test_video_jobs_listed(client):
    r = client.get("/api/video/jobs")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    assert all("job_id" in j for j in r.json())


def test_video_process_frames_gps_timeline(client, sample_video):
    with open(sample_video, "rb") as vf:
        r = client.post(
            "/api/video/process-frames",
            data={
                "detection_type": "traffic",
                "gps_start_lat": "17.3800",
                "gps_start_lng": "78.4850",
                "gps_end_lat": "17.4000",
                "gps_end_lng": "78.4980",
                "vehicle_id": "1",
                "frame_interval": "5",
            },
            files={"file": ("sample.mp4", vf, "video/mp4")},
        )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ml_service_unavailable"
    assert data["gps_timeline"]["start"]["lat"] == 17.38
    assert data["gps_timeline"]["end"]["lat"] == 17.40


def test_video_ingest_creates_records_with_challan_and_evidence(client):
    import base64
    import cv2
    import numpy as np
    from app.routers import video as video_router
    from app.models.video_job import VideoJob
    from app.database import SessionLocal

    db = SessionLocal()
    job = VideoJob(
        job_id="test-ingest-job-1",
        filename="x.mp4",
        status="processing",
        gps_start_lat=17.3600, gps_start_lng=78.4700,
        gps_end_lat=17.4200, gps_end_lng=78.5300,
        duration=10.0,
        ml_job_id="ml-ingest-1",
        vehicle_id=1,
    )
    db.add(job)
    db.commit()
    db.close()

    ok, enc = cv2.imencode(".jpg", np.zeros((100, 100, 3), dtype=np.uint8))
    b64 = base64.b64encode(enc.tobytes()).decode("ascii")

    def fake_ml_status(ml_job_id):
        return {
            "status": "completed", "progress": 100, "frames_processed": 10,
            "total_frames": 10, "video_total_frames": 100, "duration": 10.0,
            "traffic_events": 1, "pothole_events": 1,
            "detections": [
                {"event_id": "t1", "type": "traffic", "violation_type": "NO_HELMET",
                 "confidence": 0.93, "timestamp": 2.0, "bbox": [1, 2, 3, 4],
                 "frame_idx": 30, "evidence_image": b64, "vehicle_number": "TS09AB1234"},
                {"event_id": "p1", "type": "pothole", "class_name": "pothole",
                 "confidence": 0.88, "timestamp": 8.0, "bbox": [10, 10, 90, 90],
                 "frame_idx": 120, "severity": "high", "evidence_image": b64},
            ],
        }

    original = video_router._get_ml_status
    video_router._get_ml_status = fake_ml_status
    try:
        r = client.get("/api/video/status/test-ingest-job-1")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "completed"
        assert data["completed"] is True
        assert data["traffic_detections"] == 1
        assert data["pothole_detections"] == 1

        viol = next(d for d in data["detections"] if d["type"] == "traffic")
        assert viol["status"] == "AI_VERIFIED"
        assert viol["challan_status"] == "GENERATED"
        assert viol["vehicle_number"] == "TS09AB1234"
        assert viol["evidence_url"]

        phole = next(d for d in data["detections"] if d["type"] == "pothole")
        assert phole["status"] == "VERIFIED"
        assert phole["severity"] == "high"

        mx = client.get("/api/map/incidents").json()
        assert any(viol["ref"] in m["title"] for m in mx["violation_markers"])
        assert any(m["title"] == phole["ref"] for m in mx["pothole_markers"])

        stats = client.get("/api/dashboard/statistics").json()
        assert stats["video_jobs"] >= 1
    finally:
        video_router._get_ml_status = original


# ============= AUTH TESTS =============

def test_login_success_admin(client):
    r = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert r.status_code == 200
    data = r.json()
    assert data["token_type"] == "bearer"
    assert data["access_token"]
    assert data["user"]["username"] == "admin"
    assert data["user"]["role"] == "admin"


def test_login_success_officer(client):
    r = client.post("/api/auth/login", json={"username": "officer1", "password": "officer123"})
    assert r.status_code == 200
    data = r.json()
    assert data["user"]["username"] == "officer1"
    assert data["user"]["role"] == "officer"


def test_login_wrong_password(client):
    r = client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
    assert r.status_code == 401
    assert r.json()["detail"] == "Invalid username or password"


def test_login_unknown_user(client):
    r = client.post("/api/auth/login", json={"username": "ghost", "password": "x"})
    assert r.status_code == 401


def test_auth_me_with_valid_token(client):
    token = client.post("/api/auth/login", json={"username": "officer2", "password": "officer123"}).json()["access_token"]
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["username"] == "officer2"


def test_auth_me_without_token(client):
    r = client.get("/api/auth/me")
    assert r.status_code == 401


def test_auth_me_with_garbage_token(client):
    r = client.get("/api/auth/me", headers={"Authorization": "Bearer not.a.real.token"})
    assert r.status_code == 401