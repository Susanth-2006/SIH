import math
from datetime import datetime

from sqlalchemy.orm import Session


def generate_id(prefix: str, count: int) -> str:
    return f"{prefix}-{count:03d}"


def next_id(db: Session, model, id_column: str, prefix: str) -> str:
    max_n = 0
    for (value,) in db.query(getattr(model, id_column)).all():
        if not value:
            continue
        try:
            max_n = max(max_n, int(str(value).rsplit("-", 1)[-1]))
        except (ValueError, IndexError):
            continue
    return generate_id(prefix, max_n + 1)


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


VIOLATION_FINE_MAP = {
    "NO_HELMET": 500,
    "SIGNAL_JUMP": 500,
    "WRONG_ROUTE": 1000,
    "OVERSPEEDING": 500,
    "OTHER": 500,
}


def calculate_fine(violation_type: str) -> float:
    return VIOLATION_FINE_MAP.get(violation_type, 500)
