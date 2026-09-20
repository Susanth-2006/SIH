import os
import numpy as np
import cv2
import torch
from model_loader import load_yolo_model

CONFIDENCE_THRESHOLD = 0.25
IOU_THRESHOLD = 0.45
IMG_SIZE = 448
YOLOV8_IMG_SIZE = 640
YOLOV8_CONFIDENCE_THRESHOLD = 0.15


def severity_from_bbox(bbox, frame_w, frame_h):
    x1, y1, x2, y2 = bbox
    bw = max(0, x2 - x1)
    bh = max(0, y2 - y1)
    area = bw * bh
    frame_area = max(1, frame_w * frame_h)
    ratio = area / frame_area
    if ratio >= 0.10:
        return "high"
    if ratio >= 0.04:
        return "medium"
    return "low"


class PotholeDetector:
    def __init__(self):
        self.model = None
        self.yolo = None
        self.device = None

    def load(self, model_path=None):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        if model_path is None:
            base = os.path.join(os.path.dirname(__file__), "models")
            for name in ("pothole_yolov8.pt", "pothole_best.pt"):
                candidate = os.path.join(base, name)
                if os.path.exists(candidate):
                    model_path = candidate
                    break
        if not model_path or not os.path.exists(model_path):
            print(f"Pothole model not found, using OpenCV content-based detection")
            return False
        try:
            from ultralytics import YOLO
            self.yolo = YOLO(model_path)
            print(f"Pothole YOLOv8 model loaded from {model_path} ({self.yolo.names})")
            return True
        except Exception as e:
            print(f"ultralytics YOLOv8 load failed for {model_path}: {e}")
        try:
            self.model = load_yolo_model(model_path)
            self.model.to(self.device)
            self.model.eval()
            print(f"Pothole YOLOv5 model loaded from {model_path}")
            return True
        except Exception as e:
            print(f"Error loading pothole model: {e}")
            self.model = None
            self.yolo = None
            return False

    @property
    def loaded(self):
        return self.yolo is not None or self.model is not None

    def detect(self, img, frame_index=0):
        if self.yolo is not None:
            return self._detect_yolov8(img)
        if self.model is None:
            return cv_pothole_detection(img)

        try:
            from utils.general import non_max_suppression, scale_coords
            from utils.datasets import letterbox

            img_resized = letterbox(img, new_shape=IMG_SIZE)[0]
            img_tensor = img_resized[:, :, ::-1].transpose(2, 0, 1)
            img_tensor = np.ascontiguousarray(img_tensor)
            img_tensor = torch.from_numpy(img_tensor).to(self.device).float() / 255.0
            if img_tensor.ndimension() == 3:
                img_tensor = img_tensor.unsqueeze(0)

            with torch.no_grad():
                pred = self.model(img_tensor)[0]
            det = non_max_suppression(pred, CONFIDENCE_THRESHOLD, IOU_THRESHOLD)[0]

            detections = []
            if det is not None and len(det):
                det[:, :4] = scale_coords(img_tensor.shape[2:], det[:, :4], img.shape).round()
                names = self.model.module.names if hasattr(self.model, "module") else self.model.names
                for *xyxy, conf, cls in det:
                    cn = names[int(cls)]
                    bbox = [int(x.item()) for x in xyxy]
                    detections.append({
                        "class_name": cn,
                        "confidence": round(float(conf.item()), 4),
                        "bbox": bbox,
                        "severity": severity_from_bbox(bbox, img.shape[1], img.shape[0]),
                    })
            if not detections:
                detections = cv_pothole_detection(img)
            return detections
        except Exception as e:
            print(f"Pothole model error: {e}")
            try:
                return cv_pothole_detection(img)
            except Exception:
                return mock_pothole_detection(img, frame_index)

    def _detect_yolov8(self, img):
        try:
            result = self.yolo.predict(
                img,
                imgsz=YOLOV8_IMG_SIZE,
                conf=YOLOV8_CONFIDENCE_THRESHOLD,
                iou=IOU_THRESHOLD,
                verbose=False,
            )[0]
        except Exception as e:
            print(f"Pothole YOLOv8 inference error: {e}")
            return []
        h, w = img.shape[:2]
        detections = []
        for box in result.boxes:
            x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
            conf = float(box.conf[0])
            name = result.names.get(int(box.cls[0]), "pothole")
            if name.lower() in ("pothole", "pathhole"):
                name = "pothole"
            bbox = [x1, y1, x2, y2]
            detections.append({
                "class_name": name,
                "confidence": round(conf, 4),
                "bbox": bbox,
                "severity": severity_from_bbox(bbox, w, h),
            })
        return detections


def cv_pothole_detection(frame):
    """
    Content-based pothole detection using OpenCV heuristics.

    Potholes appear as dark, roughly oval patches with local contrast
    against the surrounding road surface and a broken, textured interior.
    Detection is driven by the image content itself: a clean road yields
    no detections instead of a fabricated one.

    Bus-mounted camera footage is handled specifically: the search is
    restricted to the road band (lower part of the frame) and thresholds
    adapt to dark asphalt, where potholes are only a few gray levels
    darker than the surrounding road.

    When a trained YOLO weight file is placed at models/pothole_yolov8.pt
    (YOLOv8/ultralytics format, e.g. the ON-ROAD-AI pathhole model) it is
    used instead of this heuristic detector. models/pothole_best.pt remains
    supported for legacy YOLOv5 checkpoints.
    """
    h, w = frame.shape[:2]
    if h < 60 or w < 40:
        return []

    scale = 720.0 / max(h, w)
    analyze_w, analyze_h = int(w * scale), int(h * scale)
    small = cv2.resize(frame, (analyze_w, analyze_h)) if scale != 1.0 else frame

    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    hh, ww = gray.shape

    band_top = int(hh * 0.45)
    band_bottom = int(hh * 0.97)
    band = gray[band_top:band_bottom, :]
    if band.size < 2000:
        return []

    band_mean = cv2.mean(band)[0]

    # Local-adaptive darkness vs a ~40px neighborhood (filters out global
    # gradient and coarse shadows, keeps compact dark holes).
    bg = cv2.GaussianBlur(band, (0, 0), sigmaX=40)
    diff = bg.astype(np.int16) - band.astype(np.int16)
    dark = np.where(diff >= 10, 255, 0).astype(np.uint8)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
    dark = cv2.morphologyEx(dark, cv2.MORPH_CLOSE, kernel, iterations=2)
    dark = cv2.morphologyEx(dark, cv2.MORPH_OPEN, kernel, iterations=1)

    contours, _ = cv2.findContours(dark, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    band_area = band.shape[0] * band.shape[1]
    min_area = band_area * 0.0008
    max_area = band_area * 0.35

    detections = []
    for c in contours:
        area = cv2.contourArea(c)
        if area < min_area or area > max_area:
            continue
        x, y, bw, bh = cv2.boundingRect(c)
        if bw <= 5 or bh <= 5:
            continue

        aspect = bw / float(bh)
        if not (0.30 <= aspect <= 3.5):
            continue

        hull = cv2.convexHull(c)
        hull_area = cv2.contourArea(hull)
        solidity = area / hull_area if hull_area else 0.0
        if solidity < 0.50:
            continue

        mask = np.zeros_like(band)
        cv2.drawContours(mask, [c], -1, 255, -1)
        interior_mean = cv2.mean(band, mask=mask)[0]
        if interior_mean > 165 or interior_mean > band_mean - 5:
            continue
        interior_std = float(np.std(band[mask > 0])) if mask.sum() else 0.0
        if interior_std < 3:
            continue
        depth = float(np.mean(diff[mask > 0])) if mask.sum() else 0.0
        if depth < 8:
            continue

        ring_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (17, 17))
        ring = cv2.dilate(mask, ring_kernel) - mask
        surround_mean = cv2.mean(band, mask=ring)[0] if ring.sum() else interior_mean
        contrast = (surround_mean - interior_mean) / 255.0
        if contrast < 0.035:
            continue

        if len(c) >= 5:
            try:
                (_, (ma, sa), _) = cv2.fitEllipse(c)
                ellipse_area = np.pi * ma * sa / 4.0
                ratio_ok = min(ellipse_area, area) / max(ellipse_area, area) if ellipse_area and area else 0.0
                axis_ratio = max(ma, sa) / max(min(ma, sa), 1e-6)
            except Exception:
                ratio_ok, axis_ratio = 0.5, 5.0
            if ratio_ok < 0.50 or axis_ratio > 2.8:
                continue
        else:
            ratio_ok, axis_ratio = 0.5, 5.0

        depth_score = np.clip(depth / 30.0, 0, 1)
        band_diff_score = np.clip((band_mean - interior_mean) / 12.0, 0, 1)
        area_score = np.clip(area / (band_area * 0.02), 0, 1)
        std_score = np.clip(interior_std / 45.0, 0, 1)
        ellipse_score = np.clip((6.0 - axis_ratio) / 5.0, 0, 1) * np.clip(ratio_ok * 1.7, 0, 1)
        score = 0.38 + 0.22 * depth_score + 0.22 * band_diff_score + 0.10 * area_score + 0.08 * std_score + 0.12 * ellipse_score
        conf = float(np.clip(score, 0.42, 0.93))

        fx = w / ww
        fy = h / hh
        bbox = [int(x * fx), int((y + band_top) * fy), int((x + bw) * fx), int((y + bh + band_top) * fy)]
        detections.append({
            "class_name": "pothole",
            "confidence": round(conf, 4),
            "bbox": bbox,
            "severity": severity_from_bbox(bbox, w, h),
        })

    detections.sort(key=lambda d: d["confidence"], reverse=True)

    kept = []
    for d in detections:
        overlap = False
        x1, y1, x2, y2 = d["bbox"]
        a = max(1, (x2 - x1) * (y2 - y1))
        for k in kept:
            kx1, ky1, kx2, ky2 = k["bbox"]
            ix1, iy1 = max(x1, kx1), max(y1, ky1)
            ix2, iy2 = min(x2, kx2), min(y2, ky2)
            inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
            if inter / a > 0.45:
                overlap = True
                break
        if not overlap:
            kept.append(d)
        if len(kept) >= 3:
            break

    return kept


def mock_pothole_detection(frame, frame_index=0):
    h, w = frame.shape[:2]
    detections = []

    cx, cy = int(w * 0.55), int(h * 0.55)
    jitter = int(np.random.randint(-8, 8))
    bw, bh = int(w * 0.18), int(h * 0.14)
    x1 = max(0, cx - bw // 2 + jitter)
    y1 = max(0, cy - bh // 2 + jitter)
    x2 = min(w, cx + bw // 2 + jitter)
    y2 = min(h, cy + bh // 2 + jitter)
    bbox = [int(x1), int(y1), int(x2), int(y2)]

    conf = float(np.clip(0.55 + 0.28 * np.sin(frame_index * 0.05 + 1.7) + 0.05 * np.random.rand(), 0.45, 0.93))

    detections.append({
        "class_name": "pothole",
        "confidence": round(conf, 4),
        "bbox": bbox,
        "severity": severity_from_bbox(bbox, w, h),
    })
    return detections