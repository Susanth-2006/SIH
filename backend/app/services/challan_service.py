from sqlalchemy.orm import Session
from datetime import datetime, timezone
from ..models.challan import Challan
from ..models.traffic_violation import TrafficViolation
from ..models.fleet import FleetVehicle
from ..utils.helpers import generate_id, calculate_fine, next_id
from .notification_service import create_notification


def generate_challan(db: Session, violation_id: int, officer_id: int = None) -> Challan:
    violation = db.query(TrafficViolation).filter(TrafficViolation.id == violation_id).first()
    if not violation:
        return None

    if violation.challan_status != "NOT_GENERATED":
        existing = db.query(Challan).filter(Challan.violation_id == violation_id).first()
        return existing

    fine_amount = calculate_fine(violation.violation_type)
    challan = Challan(
        challan_id=next_id(db, Challan, "challan_id", "CH"),
        violation_id=violation.id,
        vehicle_number=violation.vehicle_number,
        violation_type=violation.violation_type,
        fine_amount=fine_amount,
        detection_timestamp=violation.timestamp,
        latitude=violation.latitude,
        longitude=violation.longitude,
        evidence_path=violation.evidence_image,
        ai_confidence=violation.confidence,
        verification_status=violation.verification_status,
        challan_status="GENERATED",
        officer_id=officer_id,
    )

    violation.fine_amount = fine_amount
    violation.challan_status = "GENERATED"

    db.add(challan)
    db.commit()
    db.refresh(challan)

    create_notification(
        db,
        title=f"Challan Generated: {challan.challan_id}",
        message=f"Challan {challan.challan_id} generated for {violation.violation_type} violation. Fine: Rs.{fine_amount}",
        notification_type="CHALLAN_GENERATED",
        officer_id=officer_id,
        related_entity_type="challan",
        related_entity_id=challan.id,
    )

    return challan
