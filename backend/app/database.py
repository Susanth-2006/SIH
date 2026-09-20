from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base
from .config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
    echo=settings.DEBUG,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _migrate():
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        if "traffic_violations" in tables:
            cols = {c["name"] for c in inspector.get_columns("traffic_violations")}
            if "video_job_id" not in cols:
                with engine.begin() as conn:
                    conn.execute(text("ALTER TABLE traffic_violations ADD COLUMN video_job_id VARCHAR(40)"))
        if "potholes" in tables:
            cols = {c["name"] for c in inspector.get_columns("potholes")}
            if "video_job_id" not in cols:
                with engine.begin() as conn:
                    conn.execute(text("ALTER TABLE potholes ADD COLUMN video_job_id VARCHAR(40)"))
        if "officers" in tables:
            cols = {c["name"] for c in inspector.get_columns("officers")}
            if "password_hash" not in cols:
                with engine.begin() as conn:
                    conn.execute(text("ALTER TABLE officers ADD COLUMN password_hash VARCHAR(255)"))
    except Exception as e:
        print(f"Migration warning: {e}")


def init_db():
    Base.metadata.create_all(bind=engine)
    _migrate()
