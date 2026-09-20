from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database import get_db
from ..models.challan import Challan
from ..schemas.challan import ChallanCreate, ChallanResponse, ChallanUpdate
from ..services.challan_service import generate_challan

router = APIRouter(prefix="/api/challans", tags=["challans"])


@router.post("/generate/{violation_id}", response_model=ChallanResponse)
def create_challan(violation_id: int, db: Session = Depends(get_db)):
    challan = generate_challan(db, violation_id)
    if not challan:
        raise HTTPException(status_code=404, detail="Violation not found or challan already exists")
    return challan


@router.get("/", response_model=List[ChallanResponse])
def list_challans(
    skip: int = 0,
    limit: int = 100,
    challan_status: Optional[str] = None,
    vehicle_number: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Challan)
    if challan_status:
        query = query.filter(Challan.challan_status == challan_status)
    if vehicle_number:
        query = query.filter(Challan.vehicle_number.contains(vehicle_number))
    return query.order_by(Challan.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/{challan_id}", response_model=ChallanResponse)
def get_challan(challan_id: int, db: Session = Depends(get_db)):
    challan = db.query(Challan).filter(Challan.id == challan_id).first()
    if not challan:
        raise HTTPException(status_code=404, detail="Challan not found")
    return challan


@router.patch("/{challan_id}", response_model=ChallanResponse)
def update_challan(challan_id: int, update: ChallanUpdate, db: Session = Depends(get_db)):
    challan = db.query(Challan).filter(Challan.id == challan_id).first()
    if not challan:
        raise HTTPException(status_code=404, detail="Challan not found")
    for key, value in update.model_dump(exclude_unset=True).items():
        setattr(challan, key, value)
    db.commit()
    db.refresh(challan)
    return challan
