import os
import httpx
from ..config import settings


async def call_ml_service_detection(video_path: str = None, image_path: str = None, frame_data: bytes = None):
    ml_url = settings.ML_SERVICE_URL

    if frame_data:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{ml_url}/detect/traffic",
                files={"frame": ("frame.jpg", frame_data, "image/jpeg")},
            )
            return response.json()
    elif image_path:
        async with httpx.AsyncClient(timeout=120.0) as client:
            with open(image_path, "rb") as f:
                response = await client.post(
                    f"{ml_url}/detect/traffic",
                    files={"frame": (os.path.basename(image_path), f, "image/jpeg")},
                )
                return response.json()
    elif video_path:
        async with httpx.AsyncClient(timeout=300.0) as client:
            with open(video_path, "rb") as f:
                response = await client.post(
                    f"{ml_url}/detect/traffic/video",
                    files={"video": (os.path.basename(video_path), f, "video/mp4")},
                )
                return response.json()
    return None


async def call_ml_service_pothole(image_path: str = None, frame_data: bytes = None):
    ml_url = settings.ML_SERVICE_URL

    if frame_data:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{ml_url}/detect/pothole",
                files={"frame": ("frame.jpg", frame_data, "image/jpeg")},
            )
            return response.json()
    elif image_path:
        async with httpx.AsyncClient(timeout=120.0) as client:
            with open(image_path, "rb") as f:
                response = await client.post(
                    f"{ml_url}/detect/pothole",
                    files={"frame": (os.path.basename(image_path), f, "image/jpeg")},
                )
                return response.json()
    return None
