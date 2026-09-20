from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from ..database import get_db
from ..models.officer import Officer
from ..security import create_access_token, decode_access_token, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest, db=Depends(get_db)):
    officer = db.query(Officer).filter(Officer.username == req.username).first()
    if not officer or not officer.is_active:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    if officer.password_hash and not verify_password(req.password, officer.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    if not officer.password_hash:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = create_access_token(officer.id, officer.username, officer.role)
    return LoginResponse(
        access_token=token,
        token_type="bearer",
        user={
            "id": officer.id,
            "username": officer.username,
            "name": officer.name,
            "email": officer.email,
            "role": officer.role,
        },
    )


def get_current_officer(authorization: str = Header(default=""), db=Depends(get_db)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_access_token(authorization[7:])
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    officer = db.query(Officer).filter(Officer.id == payload.get("sub")).first()
    if not officer or not officer.is_active:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return officer


@router.get("/me")
def me(officer: Officer = Depends(get_current_officer)):
    return {
        "id": officer.id,
        "username": officer.username,
        "name": officer.name,
        "email": officer.email,
        "role": officer.role,
    }