from fastapi import APIRouter, Depends
from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session
from ..database import get_db
from ..schemas.map import MapIncidentsResponse, MapMarker, RoutePolyline, DashboardStats
from ..models.fleet import FleetVehicle, GPSPoint
from ..models.pothole import Pothole
from ..models.traffic_violation import TrafficViolation
from ..models.challan import Challan

router = APIRouter(prefix="/api", tags=["map", "dashboard"])


@router.get("/map/incidents", response_model=MapIncidentsResponse)
def get_map_incidents(db: Session = Depends(get_db)):
    fleet_markers = []
    vehicles = db.query(FleetVehicle).filter(FleetVehicle.is_active == True).all()
    for v in vehicles:
        if v.current_lat and v.current_lng:
            fleet_markers.append(MapMarker(
                id=f"fleet-{v.id}",
                type="fleet",
                latitude=v.current_lat,
                longitude=v.current_lng,
                title=f"{v.fleet_id} - {v.vehicle_number}",
                status="active" if v.gps_status == "active" else "offline",
                details={"fleet_id": v.fleet_id, "vehicle_number": v.vehicle_number, "route": v.route_name},
            ))

    pothole_markers = []
    potholes = db.query(Pothole).filter(Pothole.status.notin_(["REJECTED"])).all()
    for p in potholes:
        pothole_markers.append(MapMarker(
            id=f"pothole-{p.id}",
            type="pothole",
            latitude=p.latitude,
            longitude=p.longitude,
            title=p.pothole_id,
            status=p.status,
            confidence=p.confidence,
            details={"severity": p.severity, "detected_by": p.detected_by_vehicle_id},
        ))

    violation_markers = []
    violations = db.query(TrafficViolation).filter(TrafficViolation.status.notin_(["REJECTED"])).all()
    for v in violations:
        if v.latitude and v.longitude:
            violation_markers.append(MapMarker(
                id=f"violation-{v.id}",
                type="traffic_violation",
                latitude=v.latitude,
                longitude=v.longitude,
                title=f"{v.violation_id} - {v.violation_type}",
                status=v.verification_status,
                confidence=v.confidence,
                details={
                    "vehicle_number": v.vehicle_number,
                    "challan_status": v.challan_status,
                    "fine_amount": v.fine_amount,
                },
            ))

    routes = []
    for v in vehicles:
        points = (
            db.query(GPSPoint)
            .filter(GPSPoint.vehicle_id == v.id)
            .order_by(GPSPoint.timestamp.asc())
            .limit(500)
            .all()
        )
        if points:
            route_points = [{"lat": p.latitude, "lng": p.longitude} for p in points]
            colors = ["#4285F4", "#EA4335", "#FBBC04", "#34A853", "#FF6D01", "#46BDC6"]
            color = colors[v.id % len(colors)]
            routes.append(RoutePolyline(
                vehicle_id=f"fleet-{v.id}",
                vehicle_number=v.vehicle_number,
                points=route_points,
                color=color,
            ))

    return MapIncidentsResponse(
        fleet_markers=fleet_markers,
        pothole_markers=pothole_markers,
        violation_markers=violation_markers,
        routes=routes,
    )


@router.get("/dashboard/statistics", response_model=DashboardStats)
def get_dashboard_stats(db: Session = Depends(get_db)):
    fleet_active = db.query(FleetVehicle).filter(FleetVehicle.is_active == True, FleetVehicle.gps_status == "active").count()
    fleet_offline = db.query(FleetVehicle).filter(FleetVehicle.is_active == True, FleetVehicle.gps_status != "active").count()
    vehicles_tracked = db.query(FleetVehicle).filter(FleetVehicle.is_active == True).count()

    potholes_total = db.query(Pothole).count()
    potholes_pending = db.query(Pothole).filter(Pothole.status == "PENDING_VERIFICATION").count()
    potholes_verified = db.query(Pothole).filter(Pothole.status == "VERIFIED").count()
    potholes_work_started = db.query(Pothole).filter(Pothole.status == "WORK_STARTED").count()
    potholes_work_finished = db.query(Pothole).filter(Pothole.status == "WORK_FINISHED").count()
    potholes_fixed = db.query(Pothole).filter(Pothole.status == "FIXED").count()
    potholes_repair_failed = db.query(Pothole).filter(Pothole.status == "REPAIR_FAILED").count()

    violations_total = db.query(TrafficViolation).count()
    violations_ai_verified = db.query(TrafficViolation).filter(TrafficViolation.verification_status == "AI_VERIFIED").count()
    violations_pending = db.query(TrafficViolation).filter(TrafficViolation.verification_status == "PENDING_OFFICER").count()
    violations_officer_verified = db.query(TrafficViolation).filter(TrafficViolation.verification_status == "OFFICER_VERIFIED").count()
    violations_rejected = db.query(TrafficViolation).filter(TrafficViolation.verification_status == "REJECTED").count()

    challans_generated = db.query(Challan).filter(Challan.challan_status == "GENERATED").count()
    challans_paid = db.query(Challan).filter(Challan.challan_status == "PAID").count()

    from ..models.video_job import VideoJob
    video_jobs = db.query(VideoJob).count()
    video_frames_processed = db.query(
        sa_func.coalesce(sa_func.sum(VideoJob.frames_processed), 0)
    ).scalar()
    video_processing_completed = db.query(VideoJob).filter(VideoJob.status == "completed").count()

    return DashboardStats(
        fleet_active=fleet_active,
        fleet_offline=fleet_offline,
        vehicles_tracked=vehicles_tracked,
        potholes_total=potholes_total,
        potholes_pending=potholes_pending,
        potholes_verified=potholes_verified,
        potholes_work_started=potholes_work_started,
        potholes_work_finished=potholes_work_finished,
        potholes_fixed=potholes_fixed,
        potholes_repair_failed=potholes_repair_failed,
        violations_total=violations_total,
        violations_ai_verified=violations_ai_verified,
        violations_pending=violations_pending,
        violations_officer_verified=violations_officer_verified,
        violations_rejected=violations_rejected,
        challans_generated=challans_generated,
        challans_paid=challans_paid,
        video_jobs=video_jobs,
        video_frames_processed=int(video_frames_processed or 0),
        video_processing_completed=video_processing_completed,
    )
