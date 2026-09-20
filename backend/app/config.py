import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./urban_intelligence.db")
    GOOGLE_MAPS_API_KEY: str = os.getenv("GOOGLE_MAPS_API_KEY", "")
    ML_SERVICE_URL: str = os.getenv("ML_SERVICE_URL", "http://localhost:8001")
    PLATERECOGNIZER_TOKEN: str = os.getenv("PLATERECOGNIZER_TOKEN", "")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key")
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./backend/uploads")

    SAMPLE_VIDEO_DIR: str = os.getenv(
        "SAMPLE_VIDEO_DIR",
        os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "test_images_videos")),
    )
    SEED_DEMO_DETECTIONS: bool = os.getenv("SEED_DEMO_DETECTIONS", "true").lower() == "true"

    CONFIDENCE_THRESHOLD: float = 0.80
    AUTO_REJECT_CONFIDENCE: float = 0.20
    POOTHOLE_GPS_PROXIMITY_METERS: float = 50.0

    class Config:
        env_file = ".env"


settings = Settings()
