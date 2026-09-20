import os
import uuid
import base64
import threading
import traceback
import cv2
import numpy as np

from pothole_detector import severity_from_bbox
from ocr_service import extract_plate


def _encode_jpeg_b64(img):
    ok, encoded = cv2.imencode(".jpg", img)
    if not ok:
        return None
    return base64.b64encode(encoded.tobytes()).decode("ascii")


def _crop_b64(frame, bbox):
    h, w = frame.shape[:2]
    x1, y1, x2, y2 = [int(v) for v in bbox]
    pad = 8
    x1 = max(0, x1 - pad)
    y1 = max(0, y1 - pad)
    x2 = min(w, x2 + pad)
    y2 = min(h, y2 + pad)
    crop = frame[y1:y2, x1:x2]
    if crop.size == 0:
        crop = frame
    return _encode_jpeg_b64(crop)


def _iou(a, b):
    x1 = max(a[0], b[0])
    y1 = max(a[1], b[1])
    x2 = min(a[2], b[2])
    y2 = min(a[3], b[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    a_area = max(0, a[2] - a[0]) * max(0, a[3] - a[1])
    b_area = max(0, b[2] - b[0]) * max(0, b[3] - b[1])
    union = a_area + b_area - inter
    return inter / union if union > 0 else 0.0


def _centroid_dist(a, b):
    ca = ((a[0] + a[2]) / 2.0, (a[1] + a[3]) / 2.0)
    cb = ((b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0)
    return float(np.hypot(ca[0] - cb[0], ca[1] - cb[1]))


class VideoProcessor:
    def __init__(self, traffic_detector, pothole_detector, ocr_token=None):
        self.traffic = traffic_detector
        self.pothole = pothole_detector
        self.ocr_token = ocr_token
        self._lock = threading.Lock()
        self.jobs = {}

    def start_job(self, video_path, filename, frame_interval=20, min_confidence=0.40):
        job_id = uuid.uuid4().hex[:12]
        job = {
            "job_id": job_id,
            "filename": filename,
            "video_path": video_path,
            "frame_interval": int(frame_interval) or 20,
            "min_confidence": float(min_confidence) or 0.40,
            "status": "running",
            "progress": 0.0,
            "frames_processed": 0,
            "total_frames": 0,
            "video_total_frames": 0,
            "video_fps": 0.0,
            "duration": 0.0,
            "traffic_events": 0,
            "pothole_events": 0,
            "detections": [],
            "error": None,
        }
        with self._lock:
            self.jobs[job_id] = job
        thread = threading.Thread(target=self._run, args=(job_id,), daemon=True)
        thread.start()
        return job_id

    def get_status(self, job_id):
        with self._lock:
            job = self.jobs.get(job_id)
            if not job:
                return None
            return {k: v for k, v in job.items()}

    def _run(self, job_id):
        with self._lock:
            job = self.jobs.get(job_id)
        if job is None:
            return
        try:
            cap = cv2.VideoCapture(job["video_path"])
            if not cap.isOpened():
                raise RuntimeError("Could not open video file")
            total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
            interval = max(1, job["frame_interval"])
            sampled_total = max(1, int(total / interval)) if total else 0
            with self._lock:
                job["total_frames"] = sampled_total
                job["video_total_frames"] = total
                job["video_fps"] = round(float(fps), 2)
                job["duration"] = round(float(total / fps), 2) if total else 0.0

            events = {}
            order = []
            idx = 0
            processed = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                if idx % interval == 0:
                    self._process_frame(job, frame, round(idx / fps, 3), idx, events, order)
                    processed += 1
                    with self._lock:
                        job["frames_processed"] = processed
                        if sampled_total:
                            job["progress"] = round(100.0 * processed / sampled_total, 1)
                idx += 1
            cap.release()

            detections = self._finalize_events(events, order)
            with self._lock:
                job["detections"] = detections
                job["traffic_events"] = sum(1 for d in detections if d["type"] == "traffic")
                job["pothole_events"] = sum(1 for d in detections if d["type"] == "pothole")
                job["status"] = "completed"
                job["progress"] = 100.0
        except Exception as e:
            traceback.print_exc()
            with self._lock:
                job["status"] = "error"
                job["error"] = str(e)

    def _process_frame(self, job, frame, ts, idx, events, order):
        traffic_dets = []
        try:
            traffic_dets = self.traffic.detect(frame)
        except Exception as e:
            print(f"Traffic detection error at frame {idx}: {e}")

        pothole_dets = []
        try:
            pothole_dets = self.pothole.detect(frame, frame_index=idx)
        except Exception as e:
            print(f"Pothole detection error at frame {idx}: {e}")

        min_conf = job["min_confidence"]
        for d in traffic_dets:
            if d.get("violation_type") in (None, "CORRECT"):
                continue
            if d.get("confidence", 0) < min_conf:
                continue
            self._track(job, events, order, "traffic", d["violation_type"], float(d["confidence"]),
                        d["bbox"], d.get("sub_detections", []), d.get("lp_image"), frame, ts, idx)

        for d in pothole_dets:
            if d.get("confidence", 0) < min_conf:
                continue
            self._track(job, events, order, "pothole", d.get("class_name", "pothole"), float(d["confidence"]),
                        d["bbox"], [], None, frame, ts, idx)

    def _track(self, job, events, order, etype, label, conf, bbox, sub, lp_image, frame, ts, idx):
        best_key = None
        best_score = 0.0
        window = max(30, job["frame_interval"] * 4)
        for key in reversed(order):
            ev = events[key]
            if ev["type"] != etype or ev["label"] != label:
                continue
            if idx - ev["last_frame_idx"] > window:
                continue
            score = max(_iou(ev["last_bbox"], bbox), 1.0 - _centroid_dist(ev["last_bbox"], bbox) / 60.0)
            if score > best_score:
                best_score = score
                best_key = key

        if best_key is not None and best_score >= 0.25:
            ev = events[best_key]
            ev["frame_count"] += 1
            ev["last_bbox"] = bbox
            ev["last_frame_idx"] = idx
            ev["last_ts"] = ts
            if conf > ev["best_conf"]:
                ev["best_conf"] = conf
                ev["best_frame_idx"] = idx
                ev["best_bbox"] = bbox
                ev["best_ts"] = ts
                ev["frame"] = frame
                if sub:
                    ev["sub_detections"] = sub
                if lp_image is not None:
                    ev["lp_image"] = lp_image
            return

        base = f"{etype}_{idx // job['frame_interval']}"
        key = base
        n = 0
        while key in events:
            n += 1
            key = f"{base}_{n}"
        events[key] = {
            "type": etype,
            "label": label,
            "best_conf": conf,
            "best_frame_idx": idx,
            "best_bbox": bbox,
            "best_ts": ts,
            "frame": frame,
            "sub_detections": sub,
            "lp_image": lp_image,
            "first_frame_idx": idx,
            "first_ts": ts,
            "last_frame_idx": idx,
            "last_ts": ts,
            "last_bbox": bbox,
            "frame_count": 1,
        }
        order.append(key)

    def _finalize_events(self, events, order):
        detections = []
        for key in order:
            ev = events[key]
            frame = ev["frame"]
            if frame is None:
                continue
            h, w = frame.shape[:2]
            bbox = ev["best_bbox"]
            common = {
                "event_id": key,
                "frame_idx": ev["best_frame_idx"],
                "timestamp": round(float(ev["best_ts"]), 2),
                "first_frame_idx": ev["first_frame_idx"],
                "first_timestamp": round(float(ev["first_ts"]), 2),
                "frames_in_event": ev["frame_count"],
            }
            if ev["type"] == "traffic":
                vehicle_number = None
                if ev.get("lp_image") is not None and self.ocr_token:
                    try:
                        vehicle_number = extract_plate(ev["lp_image"], self.ocr_token)
                    except Exception as e:
                        print(f"OCR error: {e}")
                detections.append({
                    **common,
                    "type": "traffic",
                    "violation_type": ev["label"],
                    "confidence": round(float(ev["best_conf"]), 4),
                    "bbox": [int(x) for x in bbox],
                    "vehicle_number": vehicle_number,
                    "sub_detections": [
                        {"class": s["class"], "confidence": s["confidence"]}
                        for s in ev.get("sub_detections", []) if "class" in s
                    ],
                    "evidence_image": _crop_b64(frame, bbox),
                })
            else:
                if ev["frame_count"] < 2:
                    # Single-frame hits are considered noise; a pothole event is
                    # only confirmed after being observed in >=2 sampled frames.
                    ev["frame"] = None
                    continue
                detections.append({
                    **common,
                    "type": "pothole",
                    "class_name": ev["label"],
                    "confidence": round(float(ev["best_conf"]), 4),
                    "bbox": [int(x) for x in bbox],
                    "severity": severity_from_bbox(bbox, w, h),
                    "evidence_image": _crop_b64(frame, bbox),
                })
            ev["frame"] = None
        return detections