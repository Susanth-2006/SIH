from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from ..database import get_db
from ..models.traffic_violation import TrafficViolation, TrafficEvidence
from ..schemas.traffic_violation import (
    TrafficViolationCreate, TrafficViolationResponse,
    TrafficViolationVerify, TrafficViolationWithEvidence, TrafficEvidenceResponse,
)
from ..utils.helpers import generate_id, calculate_fine, next_id
from ..services.notification_service import create_notification
from ..services.challan_service import generate_challan
from ..config import settings
import os
import uuid

router = APIRouter(prefix="/api/traffic", tags=["traffic"])


@router.post("/detect", response_model=TrafficViolationResponse)
def detect_violation(violation: TrafficViolationCreate, db: Session = Depends(get_db)):
    new_violation = TrafficViolation(
        violation_id=next_id(db, TrafficViolation, "violation_id", "TV"),
        violation_type=violation.violation_type,
        vehicle_number=violation.vehicle_number,
        timestamp=violation.timestamp or datetime.utcnow(),
        latitude=violation.latitude,
        longitude=violation.longitude,
        confidence=violation.confidence,
        evidence_image=violation.evidence_image,
        evidence_video=violation.evidence_video,
        detection_details=violation.detection_details,
        detected_by_vehicle_id=violation.detected_by_vehicle_id,
    )

    if violation.confidence >= settings.CONFIDENCE_THRESHOLD:
        new_violation.status = "AI_DETECTED"
        new_violation.verification_status = "AI_VERIFIED"
    elif violation.confidence < settings.AUTO_REJECT_CONFIDENCE:
        new_violation.status = "REJECTED"
        new_violation.verification_status = "REJECTED"
    else:
        new_violation.status = "PENDING_VERIFICATION"
        new_violation.verification_status = "PENDING_OFFICER"

    db.add(new_violation)
    db.commit()
    db.refresh(new_violation)

    if violation.confidence >= settings.CONFIDENCE_THRESHOLD:
        generate_challan(db, new_violation.id)
        create_notification(
            db,
            title=f"Traffic Violation AI Verified: {new_violation.violation_id}",
            message=f"{violation.violation_type} detected with {violation.confidence*100:.1f}% confidence. Auto-verified. Challan generated.",
            notification_type="VIOLATION_AI_VERIFIED",
            related_entity_type="traffic_violation",
            related_entity_id=new_violation.id,
        )
    elif violation.confidence < settings.AUTO_REJECT_CONFIDENCE:
        create_notification(
            db,
            title=f"Traffic Violation Auto-Rejected: {new_violation.violation_id}",
            message=f"{violation.violation_type} detected with only {violation.confidence*100:.1f}% confidence. Below the auto-reject threshold, ignored.",
            notification_type="VIOLATION_REJECTED",
            related_entity_type="traffic_violation",
            related_entity_id=new_violation.id,
        )
    else:
        create_notification(
            db,
            title=f"Traffic Violation Requires Verification: {new_violation.violation_id}",
            message=f"{violation.violation_type} detected with {violation.confidence*100:.1f}% confidence. Requires officer verification.",
            notification_type="VIOLATION_VERIFICATION_NEEDED",
            related_entity_type="traffic_violation",
            related_entity_id=new_violation.id,
        )

    return new_violation


@router.get("/violations", response_model=List[TrafficViolationResponse])
def list_violations(
    skip: int = 0,
    limit: int = 100,
    violation_type: Optional[str] = None,
    status: Optional[str] = None,
    verification_status: Optional[str] = None,
    challan_status: Optional[str] = None,
    vehicle_number: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(TrafficViolation)
    if violation_type:
        query = query.filter(TrafficViolation.violation_type == violation_type)
    if status:
        query = query.filter(TrafficViolation.status == status)
    if verification_status:
        query = query.filter(TrafficViolation.verification_status == verification_status)
    if challan_status:
        query = query.filter(TrafficViolation.challan_status == challan_status)
    if vehicle_number:
        query = query.filter(TrafficViolation.vehicle_number.contains(vehicle_number))
    return query.order_by(TrafficViolation.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/violations/{violation_id}", response_model=TrafficViolationWithEvidence)
def get_violation(violation_id: int, db: Session = Depends(get_db)):
    violation = db.query(TrafficViolation).filter(TrafficViolation.id == violation_id).first()
    if not violation:
        raise HTTPException(status_code=404, detail="Violation not found")
    return violation


@router.post("/violations/{violation_id}/verify", response_model=TrafficViolationResponse)
def verify_violation(violation_id: int, verify: TrafficViolationVerify, db: Session = Depends(get_db)):
    violation = db.query(TrafficViolation).filter(TrafficViolation.id == violation_id).first()
    if not violation:
        raise HTTPException(status_code=404, detail="Violation not found")
    if violation.verification_status not in ["PENDING_OFFICER"]:
        raise HTTPException(status_code=400, detail="Violation is not pending verification")

    violation.status = "VERIFIED"
    violation.verification_status = "OFFICER_VERIFIED"
    violation.verified_by_officer_id = verify.officer_id

    db.commit()
    db.refresh(violation)

    generate_challan(db, violation.id, verify.officer_id)

    create_notification(
        db,
        title=f"Violation Officer Verified: {violation.violation_id}",
        message=f"{violation.violation_type} violation has been verified by officer. Challan generated.",
        notification_type="VIOLATION_OFFICER_VERIFIED",
        officer_id=verify.officer_id,
        related_entity_type="traffic_violation",
        related_entity_id=violation.id,
    )

    _apply_decision_to_duplicates(db, violation, "VERIFIED", verify.officer_id)

    return violation


def _apply_decision_to_duplicates(db: Session, source, decision: str, officer_id: int):
    if not source.vehicle_number or source.vehicle_number == "UNKNOWN":
        return
    if decision not in ("VERIFIED", "REJECTED"):
        return
    duplicates = (
        db.query(TrafficViolation)
        .filter(
            TrafficViolation.id != source.id,
            TrafficViolation.vehicle_number == source.vehicle_number,
            TrafficViolation.violation_type == source.violation_type,
            TrafficViolation.verification_status == "PENDING_OFFICER",
        )
        .all()
    )
    for dup in duplicates:
        if decision == "VERIFIED":
            dup.status = "VERIFIED"
            dup.verification_status = "OFFICER_VERIFIED"
            dup.verified_by_officer_id = officer_id
        else:
            dup.status = "REJECTED"
            dup.verification_status = "REJECTED"
            dup.verified_by_officer_id = officer_id
        db.commit()
        db.refresh(dup)
        if decision == "VERIFIED":
            generate_challan(db, dup.id, officer_id)
            create_notification(
                db,
                title=f"Duplicate Violation Auto-Verified: {dup.violation_id}",
                message=f"Same vehicle {dup.vehicle_number} / {dup.violation_type} as {source.violation_id}. Officer decision applied automatically. Challan generated.",
                notification_type="VIOLATION_OFFICER_VERIFIED",
                officer_id=officer_id,
                related_entity_type="traffic_violation",
                related_entity_id=dup.id,
            )
        else:
            create_notification(
                db,
                title=f"Duplicate Violation Auto-Rejected: {dup.violation_id}",
                message=f"Same vehicle {dup.vehicle_number} / {dup.violation_type} as {source.violation_id}. Officer decision applied automatically.",
                notification_type="VIOLATION_REJECTED",
                officer_id=officer_id,
                related_entity_type="traffic_violation",
                related_entity_id=dup.id,
            )


@router.post("/violations/{violation_id}/reject", response_model=TrafficViolationResponse)
def reject_violation(violation_id: int, verify: TrafficViolationVerify, db: Session = Depends(get_db)):
    violation = db.query(TrafficViolation).filter(TrafficViolation.id == violation_id).first()
    if not violation:
        raise HTTPException(status_code=404, detail="Violation not found")
    if violation.verification_status not in ["PENDING_OFFICER", "AI_VERIFIED"]:
        raise HTTPException(status_code=400, detail="Cannot reject this violation")

    violation.status = "REJECTED"
    violation.verification_status = "REJECTED"
    violation.verified_by_officer_id = verify.officer_id

    db.commit()
    db.refresh(violation)

    create_notification(
        db,
        title=f"Violation Rejected: {violation.violation_id}",
        message=f"{violation.violation_type} violation has been rejected by officer.",
        notification_type="VIOLATION_REJECTED",
        officer_id=verify.officer_id,
        related_entity_type="traffic_violation",
        related_entity_id=violation.id,
    )

    _apply_decision_to_duplicates(db, violation, "REJECTED", verify.officer_id)

    return violation


@router.post("/upload-evidence", response_model=TrafficEvidenceResponse)
async def upload_evidence(
    violation_id: int,
    evidence_type: str = "IMAGE",
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    violation = db.query(TrafficViolation).filter(TrafficViolation.id == violation_id).first()
    if not violation:
        raise HTTPException(status_code=404, detail="Violation not found")

    ext = os.path.splitext(file.filename)[1] if file.filename else ".jpg"
    filename = f"evidence_{violation.violation_id}_{uuid.uuid4().hex[:8]}{ext}"
    upload_dir = os.path.join(settings.UPLOAD_DIR, "evidence")
    os.makedirs(upload_dir, exist_ok=True)
    filepath = os.path.join(upload_dir, filename)

    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)

    evidence = TrafficEvidence(
        violation_id=violation.id,
        evidence_type=evidence_type,
        file_path=filepath,
        timestamp=violation.timestamp,
        latitude=violation.latitude,
        longitude=violation.longitude,
        vehicle_number=violation.vehicle_number,
        violation_type=violation.violation_type,
        confidence=violation.confidence,
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)
    return evidence
