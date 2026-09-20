from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class OfficerCreate(BaseModel):
    username: str
    name: str
    email: Optional[str] = None
    role: str = "officer"


class OfficerResponse(BaseModel):
    id: int
    username: str
    name: str
    email: Optional[str]
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
