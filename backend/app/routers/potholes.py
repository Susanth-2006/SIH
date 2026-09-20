from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from ..database import get_db
from ..models.pothole import Pothole, PotholeVerification
from ..models.fleet import FleetVehicle
from ..schemas.pothole import PotholeCreate, PotholeResponse, PotholeVerify, PotholeWorkUpdate
from ..utils.helpers import generate_id, haversine_distance, next_id
from ..services.notification_service import create_notification
from ..config import settings

router = APIRouter(prefix="/api/potholes", tags=["potholes"])


@router.post("/detect", response_model=PotholeResponse)
def detect_pothole(pothole: PotholeCreate, db: Session = Depends(get_db)):
    auto_rejected = pothole.confidence < settings.AUTO_REJECT_CONFIDENCE

    if not auto_rejected:
        for p in db.query(Pothole).all():
            dist = haversine_distance(pothole.latitude, pothole.longitude, p.latitude, p.longitude)
            if dist >= settings.POOTHOLE_GPS_PROXIMITY_METERS:
                continue

            if p.status in ["FIXED", "REPAIR_FAILED"]:
                p.status = "REPAIR_VERIFICATION_PENDING"
                p.updated_at = datetime.utcnow()
                if pothole.confidence >= p.confidence:
                    p.confidence = pothole.confidence
                if pothole.evidence_image:
                    p.evidence_image = pothole.evidence_image
                db.commit()
                db.refresh(p)
                create_notification(
                    db,
                    title=f"Pothole Re-Detected After Repair: {p.pothole_id}",
                    message=f"Pothole {p.pothole_id} was marked {p.status}. Re-detected at ({pothole.latitude:.4f}, {pothole.longitude:.4f}). Repair verification required.",
                    notification_type="POTHOLE_REPAIR_VERIFICATION_PENDING",
                    related_entity_type="pothole",
                    related_entity_id=p.id,
                )
                return p

            if p.status == "REJECTED":
                p.status = "PENDING_VERIFICATION"
                p.updated_at = datetime.utcnow()
                if pothole.confidence >= p.confidence:
                    p.confidence = pothole.confidence
                if pothole.evidence_image:
                    p.evidence_image = pothole.evidence_image
                db.commit()
                db.refresh(p)
                create_notification(
                    db,
                    title=f"Pothole Re-Queued for Verification: {p.pothole_id}",
                    message=f"Previously rejected pothole {p.pothole_id} re-detected at ({pothole.latitude:.4f}, {pothole.longitude:.4f}). Queued for officer verification.",
                    notification_type="POTHOLE_VERIFICATION_NEEDED",
                    related_entity_type="pothole",
                    related_entity_id=p.id,
                )
                return p

            if pothole.confidence >= p.confidence:
                p.confidence = pothole.confidence
                p.updated_at = datetime.utcnow()
                if pothole.evidence_image:
                    p.evidence_image = pothole.evidence_image
                db.commit()
                db.refresh(p)
            return p

    new_pothole = Pothole(
        pothole_id=next_id(db, Pothole, "pothole_id", "PH"),
        latitude=pothole.latitude,
        longitude=pothole.longitude,
        severity=pothole.severity,
        confidence=pothole.confidence,
        detected_by_vehicle_id=pothole.detected_by_vehicle_id,
        evidence_image=pothole.evidence_image,
        evidence_video=pothole.evidence_video,
        detection_details=pothole.detection_details,
    )

    if pothole.confidence >= settings.CONFIDENCE_THRESHOLD:
        new_pothole.status = "VERIFIED"
    elif auto_rejected:
        new_pothole.status = "REJECTED"
    else:
        new_pothole.status = "PENDING_VERIFICATION"

    db.add(new_pothole)
    db.commit()
    db.refresh(new_pothole)

    if pothole.confidence >= settings.CONFIDENCE_THRESHOLD:
        create_notification(
            db,
            title=f"Pothole Detected: {new_pothole.pothole_id}",
            message=f"Pothole detected with {pothole.confidence*100:.1f}% confidence at ({pothole.latitude:.4f}, {pothole.longitude:.4f}). Auto-verified.",
            notification_type="POTHOLE_DETECTED",
            related_entity_type="pothole",
            related_entity_id=new_pothole.id,
        )
    elif auto_rejected:
        create_notification(
            db,
            title=f"Pothole Auto-Rejected: {new_pothole.pothole_id}",
            message=f"Pothole detected with only {pothole.confidence*100:.1f}% confidence. Below the auto-reject threshold, ignored.",
            notification_type="POTHOLE_REJECTED",
            related_entity_type="pothole",
            related_entity_id=new_pothole.id,
        )
    else:
        create_notification(
            db,
            title=f"Pothole Requires Verification: {new_pothole.pothole_id}",
            message=f"Pothole detected with {pothole.confidence*100:.1f}% confidence. Requires officer verification.",
            notification_type="POTHOLE_VERIFICATION_NEEDED",
            related_entity_type="pothole",
            related_entity_id=new_pothole.id,
        )

    return new_pothole


@router.get("/", response_model=List[PotholeResponse])
def list_potholes(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Pothole)
    if status:
        query = query.filter(Pothole.status == status)
    if severity:
        query = query.filter(Pothole.severity == severity)
    return query.order_by(Pothole.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/{pothole_id}", response_model=PotholeResponse)
def get_pothole(pothole_id: int, db: Session = Depends(get_db)):
    pothole = db.query(Pothole).filter(Pothole.id == pothole_id).first()
    if not pothole:
        raise HTTPException(status_code=404, detail="Pothole not found")
    return pothole


@router.post("/{pothole_id}/verify", response_model=PotholeResponse)
def verify_pothole(pothole_id: int, verify: PotholeVerify, db: Session = Depends(get_db)):
    pothole = db.query(Pothole).filter(Pothole.id == pothole_id).first()
    if not pothole:
        raise HTTPException(status_code=404, detail="Pothole not found")

    if verify.action == "VERIFIED":
        pothole.status = "VERIFIED"
    elif verify.action == "REJECTED":
        pothole.status = "REJECTED"
    else:
        raise HTTPException(status_code=400, detail="Action must be VERIFIED or REJECTED")

    verification = PotholeVerification(
        pothole_id=pothole.id,
        officer_id=verify.officer_id,
        action=verify.action,
        notes=verify.notes,
    )
    db.add(verification)
    db.commit()
    db.refresh(pothole)

    create_notification(
        db,
        title=f"Pothole {verify.action}: {pothole.pothole_id}",
        message=f"Pothole {pothole.pothole_id} has been {verify.action.lower()} by officer.",
        notification_type="POTHOLE_VERIFIED",
        officer_id=verify.officer_id,
        related_entity_type="pothole",
        related_entity_id=pothole.id,
    )

    return pothole


@router.post("/{pothole_id}/start-work", response_model=PotholeResponse)
def start_work(pothole_id: int, update: PotholeWorkUpdate, db: Session = Depends(get_db)):
    pothole = db.query(Pothole).filter(Pothole.id == pothole_id).first()
    if not pothole:
        raise HTTPException(status_code=404, detail="Pothole not found")
    if pothole.status not in ["VERIFIED"]:
        raise HTTPException(status_code=400, detail="Pothole must be verified before starting work")
    pothole.status = "WORK_STARTED"
    verification = PotholeVerification(
        pothole_id=pothole.id, officer_id=update.officer_id, action="WORK_STARTED", notes=update.notes
    )
    db.add(verification)
    db.commit()
    db.refresh(pothole)
    return pothole


@router.post("/{pothole_id}/finish-work", response_model=PotholeResponse)
def finish_work(pothole_id: int, update: PotholeWorkUpdate, db: Session = Depends(get_db)):
    pothole = db.query(Pothole).filter(Pothole.id == pothole_id).first()
    if not pothole:
        raise HTTPException(status_code=404, detail="Pothole not found")
    if pothole.status not in ["WORK_STARTED"]:
        raise HTTPException(status_code=400, detail="Work must be started before finishing")
    pothole.status = "WORK_FINISHED"
    verification = PotholeVerification(
        pothole_id=pothole.id, officer_id=update.officer_id, action="WORK_FINISHED", notes=update.notes
    )
    db.add(verification)
    db.commit()
    db.refresh(pothole)

    create_notification(
        db,
        title=f"Pothole Repair Finished: {pothole.pothole_id}",
        message=f"Repair work finished for pothole {pothole.pothole_id}. Awaiting verification.",
        notification_type="POTHOLE_REPAIR_FINISHED",
        related_entity_type="pothole",
        related_entity_id=pothole.id,
    )

    return pothole


@router.post("/{pothole_id}/repair-verify", response_model=PotholeResponse)
def repair_verify(pothole_id: int, verify: PotholeVerify, db: Session = Depends(get_db)):
    pothole = db.query(Pothole).filter(Pothole.id == pothole_id).first()
    if not pothole:
        raise HTTPException(status_code=404, detail="Pothole not found")
    if pothole.status not in ["WORK_FINISHED", "REPAIR_VERIFICATION_PENDING"]:
        raise HTTPException(status_code=400, detail="Work must be finished before repair verification")

    if verify.action == "REPAIR_VERIFIED":
        pothole.status = "FIXED"
    elif verify.action == "REPAIR_FAILED":
        pothole.status = "REPAIR_FAILED"
    else:
        raise HTTPException(status_code=400, detail="Action must be REPAIR_VERIFIED or REPAIR_FAILED")

    verification = PotholeVerification(
        pothole_id=pothole.id,
        officer_id=verify.officer_id,
        action=verify.action,
        notes=verify.notes,
    )
    db.add(verification)
    db.commit()
    db.refresh(pothole)

    create_notification(
        db,
        title=f"Repair {verify.action}: {pothole.pothole_id}",
        message=f"Repair verification for pothole {pothole.pothole_id}: {verify.action}.",
        notification_type="POTHOLE_REPAIR_VERIFIED",
        officer_id=verify.officer_id,
        related_entity_type="pothole",
        related_entity_id=pothole.id,
    )

    return pothole
