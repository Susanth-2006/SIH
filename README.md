# Urban Intelligence Platform

A unified smart-city platform where public fleet vehicles (buses, vans, cars) act as mobile sensing units. Fleet cameras detect **potholes** and **traffic violations**; GPS provides exact location; AI provides detection confidence. An **80% threshold** determines whether the system auto-accepts an event or routes it to officer verification.

## Architecture

```
┌─────────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│  React Frontend      │    │  FastAPI Backend  │    │  ML Service       │
│  (localhost:3000)    │    │  (localhost:8000) │    │  (localhost:8001) │
│  Google Maps         │◄──►│  SQLite Database  │◄──►│  YOLOv5 Detection │
│  Dashboard/Pages     │    │  8 API routers   │    │  Traffic + Pothole│
└─────────────────────┘    └──────────────────┘    └──────────────────┘
```

## Components

### Backend (FastAPI + SQLAlchemy + SQLite)
- **Fleet tracking**: vehicle registration, GPS point history, route history
- **Pothole detection**: detection capture, 80% confidence workflow, duplicate detection via GPS proximity, repair workflow (verify → work → repair verify)
- **Traffic violations**: detection, 80% confidence workflow, officer verification, demo challan generation
- **Notifications**: database-stored alerts for detections, verifications, challans
- **Challans**: auto-generation for AI-verified violations, manual generation after officer verification

### ML Service (FastAPI + YOLOv5)
- **Traffic**: two-stage detection (Rider → Helmet/No Helmet/LP) using existing trained model (`runs/train/finalModel/weights/best.pt`)
- **Pothole**: detection via YOLOv5 pothole model if present at `ml-service/models/pothole_best.pt`; otherwise a built-in OpenCV content-based detector scores dark oval road patches (local-adaptive segmentation + contrast/texture/elliptical-shape scoring)
- **Video**: complete video analysis job (traffic + pothole detection in one pass, frame sampling, event tracking / duplicate merge, best-evidence-frame selection, pothole severity estimation)
- **Endpoints**: `/detect/traffic`, `/detect/traffic/video`, `/detect/pothole`, `/detect/pothole/video`, `/process/video`, `/process/video/status/{job_id}`, `/health`

### Frontend (React + Vite + Google Maps)
Pages: Dashboard, Live Map, Live Fleet, Video Analysis, Potholes, Traffic Violations, Verification Center, Challans, Repair Management, Notifications, Reports, Settings, Demo Mode.

## Getting Started

### Prerequisites
- Python 3.9+
- Node.js 18+
- npm

### Setup

```powershell
# 1. Configure environment
copy .env.example .env   # then edit with your keys

# 2. Install dependencies
.\setup.ps1
```

### Run

```powershell
.\run-platform.ps1
```

This launches three services:
- Frontend: http://localhost:3000
- Backend: http://localhost:8000 (API docs at /docs)
- ML Service: http://localhost:8001

### Or run manually

```bash
# Terminal 1 - Backend
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 - ML Service
cd ml-service
python main.py

# Terminal 3 - Frontend
cd frontend
npm install
npm run dev
```

## Demo Data

On first startup, the backend seeds demo data automatically:
- 5 fleet vehicles (F-101 through F-105)
- 3 officers
- 5 potholes in various workflow states
- 5 traffic violations in various states

Additional demo tools available in the **Demo Mode** page:
- Seed/reset demo data
- Simulate fleet GPS movement
- Add demo potholes/violations

## Video Analysis (primary flow)

The **Video Analysis** page (sidebar → Video Analysis) is the main entry: select a bus-camera video from `test_images_videos/` and the system analyzes the whole video for traffic violations **and** potholes in a single background job.

```
Select bus footage (`final 3.mp4` by default)
  → sample frames (every FRAME_INTERVAL frame)
  → traffic detector (two-stage rider → helmet/plate) + pothole detector (severity estimate, events confirmed only when seen in >=2 sampled frames)
  → merge duplicate detections (IoU / GPS proximity) into events
  → pick best evidence frame (highest confidence) per event
  → OCR plate via PlateRecognizer (if PLATERECOGNIZER_TOKEN is set; non-fatal on failure)
  → bus GPS route: 16 interpolated GPSPoints recorded for the assigned bus at job completion → polyline drawn on the map
  → confidence >= CONFIDENCE_THRESHOLD (default 0.80):
        traffic → AI_VERIFIED → challan auto-generated
        pothole → VERIFIED → repair workflow
    confidence < threshold → PENDING_OFFICER → Verification Center → officer VERIFY/REJECT
  → evidence image saved to backend/uploads/evidence/video/<job_id>/, served at /media
  → events, challans, notifications, stats, map, reports updated
```

Track progress with job polling (`GET /api/video/status/{job_id}`); finished detections are ingested into the database once. Recent jobs are listed under `GET /api/video/jobs`.

- Potholes are detected by a real trained YOLOv8 model: `ml-service/models/pothole_yolov8.pt` (the fine-tuned ON-ROAD-AI `pathhole` model, single class, imgsz 640). A legacy YOLOv5 checkpoint at `ml-service/models/pothole_best.pt` is also honored. If no weight file is present the built-in OpenCV content-based detector is used as a fallback (local-adaptive dark-region segmentation + oval/contrast/texture scoring), so detection still follows the actual video content rather than a fixed simulated location.
- Traffic detections only appear for real riders in frame (no fabrications); a video with no riders yields no traffic events.
- Floats `CONFIDENCE_THRESHOLD` and `POOTHOLE_GPS_PROXIMITY_METERS` are read from `.env`.

## Database Schema

```
FleetVehicle
├── GPSPoint (history)
├── Pothole (detections)
└── TrafficViolation (detections)

Pothole
├── PotholeVerification (officer actions)
└── Repairs (state machine: VERIFIED → WORK_STARTED → WORK_FINISHED → FIXED)

TrafficViolation
├── TrafficEvidence
└── Challan

Officer
├── Verifications
└── Notifications
```

## API Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/fleet/ | Register fleet vehicle |
| GET | /api/fleet/ | List fleet |
| POST | /api/fleet/{id}/location | Update GPS location |
| GET | /api/fleet/{id}/route | Get route history |
| POST | /api/potholes/detect | Submit pothole detection |
| GET | /api/potholes/ | List potholes |
| POST | /api/potholes/{id}/verify | Verify/reject pothole |
| POST | /api/potholes/{id}/start-work | Start repair |
| POST | /api/potholes/{id}/finish-work | Finish repair |
| POST | /api/potholes/{id}/repair-verify | Verify repair |
| POST | /api/traffic/detect | Submit violation detection |
| GET | /api/traffic/violations | List violations |
| POST | /api/traffic/violations/{id}/verify | Verify violation |
| POST | /api/traffic/violations/{id}/reject | Reject violation |
| POST | /api/challans/generate/{id} | Generate challan |
| GET | /api/challans/ | List challans |
| GET | /api/map/incidents | Map data (fleet + potholes + violations) |
| GET | /api/dashboard/statistics | Dashboard stats |
| GET | /api/notifications/ | List notifications |
| GET | /api/video/sample-videos | List the bus-camera videos available in `test_images_videos/` (no upload is required) |
| POST | /api/video/process | Select a bus video → background job analyzes BOTH traffic violations and potholes. Form: sample_filename (or legacy file), vehicle_id, gps_start_lat/lng, gps_end_lat/lng, frame_interval, min_confidence → returns job_id |
| GET | /api/video/status/{job_id} | Live job progress + ingests finished detections (evidence, GPS, auto-verify/challan, notifications, repair workflow) |
| GET | /api/video/jobs | List recent video analysis jobs |
| POST | /api/video/process-frames | Upload & process a single detection type synchronously with GPS timeline interpolation |
| POST | /api/demo/seed | Seed demo data |
| POST | /api/demo/simulate-fleet | Simulate fleet GPS movement (JSON body) |
| POST | /api/demo/add-pothole | Add demo pothole (JSON body) |
| POST | /api/demo/add-violation | Add demo violation (JSON body) |

## Confidence Workflow

**Traffic violations & potholes:**

```
Detection → confidence >= 80%
    → AI_VERIFIED → Auto-challan (traffic) / auto-verify (pothole) → notify

Detection → confidence < 80%
    → PENDING_OFFICER → Verification Center → Officer VERIFY/REJECT
    → Officer verifies → OFFICER_VERIFIED → Generate challan
```

## Authentication

The platform has an officer login page (`/login`). All app routes are gated behind it; the backend issues signed bearer tokens.

**Demo accounts:**

| Username | Password | Role |
|----------|----------|------|
| admin | admin123 | admin |
| officer1 | officer123 | officer |
| officer2 | officer123 | officer |

- Tokens are stored in `localStorage` and sent as `Authorization: Bearer <token>`.
- `POST /api/auth/login` and `GET /api/auth/me` are the auth endpoints. Existing REST endpoints remain open (front-end gate) so integrations and tests keep working.
- Default passwords are set on startup if missing (see `ensure_officer_passwords` in `backend/app/main.py`).

## Evidence Management

Evidence for violations/potholes:
- Original video reference
- Extracted evidence frame
- Timestamp
- GPS location
- Detected vehicle
- Violation type
- Confidence
- Number plate / OCR result where available

## Google Maps

Configured via `VITE_GOOGLE_MAPS_API_KEY` in `frontend/.env`. The map shows:
- Fleet markers (blue)
- Pothole markers (color-coded by status)
- Traffic violation markers (color-coded by verification status)
- Fleet route polylines
- Layer toggles

## Security

- API keys stored in `.env` files (gitignored)
- Never expose backend API keys in frontend code
- Google Maps JS key is embedded in the frontend bundle (standard for the Maps JS API)

## Testing

```bash
# Backend tests (from backend/)
python -m pytest tests/ -v
```

## Notes

- The challan system generates **demo challans** for project demonstration. This is explicitly NOT a real government/legal challan integration.
- The ML service falls back to OpenCV content-based detection (potholes) or simulation (traffic, model absent) when model weights are unavailable, enabling distributed/demo use.
- Pothole detection uses the built-in OpenCV content-based detector until you drop a trained YOLOv5 model at `ml-service/models/pothole_best.pt` (same YOLOv5 format as the traffic model).
- For production: rotate the Google Maps API key shown in `frontend/.env`, set a real `PLATERECOGNIZER_TOKEN` for license-plate OCR, and verify map rendering in a real browser.