import os
import base64
import cv2

OCR_URL = "https://api.platerecognizer.com/v1/plate-reader/"


def extract_plate(plate_image, token=None):
    if token is None:
        token = os.getenv("PLATERECOGNIZER_TOKEN", "")
    if not token:
        return None
    if plate_image is None or plate_image.size == 0:
        return None
    try:
        import httpx
        ok, encoded = cv2.imencode(".jpg", plate_image)
        if not ok:
            return None
        response = httpx.post(
            OCR_URL,
            headers={"Authorization": f"Token {token}"},
            files={"upload": ("plate.jpg", encoded.tobytes(), "image/jpeg")},
            data={"regions": "in"},
            timeout=10.0,
        )
        if response.status_code != 200:
            return None
        results = response.json().get("results", [])
        for plate_group in results:
            candidates = plate_group.get("candidates", [])
            for cand in candidates:
                if cand.get("score", 0) > 0.5:
                    plate = cand.get("plate", "")
                    if plate:
                        return plate.upper()
    except Exception as e:
        print(f"OCR error: {e}")
    return None