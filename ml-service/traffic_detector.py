import os
import cv2
import numpy as np
import torch
from model_loader import load_yolo_model

CONFIDENCE_THRESHOLD = 0.25
IOU_THRESHOLD = 0.45
IMG_SIZE = 448
CROP_IMG_SIZE = 512

TRAFFIC_CLASSES = {0: "Helmet", 1: "No Helmet", 2: "Rider", 3: "LP"}


class TrafficDetector:
    def __init__(self):
        self.model = None
        self.device = None

    def load(self, model_path=None):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        if model_path is None:
            candidates = [
                os.path.join(os.path.dirname(__file__), "..", "runs", "train", "finalModel", "weights", "best.pt"),
                os.path.join(os.path.dirname(__file__), "..", "..", "runs", "train", "finalModel", "weights", "best.pt"),
            ]
            model_path = next((p for p in candidates if os.path.exists(p)), None)
        if not model_path or not os.path.exists(model_path):
            print(f"Traffic model not found, using mock detection")
            return False
        self.model = load_yolo_model(model_path)
        self.model.to(self.device)
        self.model.eval()
        print(f"Traffic model loaded from {model_path} on {self.device}")
        return True

    @property
    def loaded(self):
        return self.model is not None

    def _class_names(self):
        if hasattr(self.model, "module"):
            return self.model.module.names
        return self.model.names

    def _infer(self, img, size=None):
        from utils.general import non_max_suppression, scale_coords
        from utils.datasets import letterbox

        img_resized = letterbox(img, new_shape=size or IMG_SIZE)[0]
        img_tensor = img_resized[:, :, ::-1].transpose(2, 0, 1)
        img_tensor = np.ascontiguousarray(img_tensor)
        img_tensor = torch.from_numpy(img_tensor).to(self.device).float() / 255.0
        if img_tensor.ndimension() == 3:
            img_tensor = img_tensor.unsqueeze(0)

        with torch.no_grad():
            pred = self.model(img_tensor)[0]
        det = non_max_suppression(pred, CONFIDENCE_THRESHOLD, IOU_THRESHOLD)[0]
        if det is not None and len(det):
            det[:, :4] = scale_coords(img_tensor.shape[2:], det[:, :4], img.shape).round()
        return det

    def detect(self, img):
        if self.model is None:
            return mock_traffic_detection(img)

        try:
            det = self._infer(img)
        except Exception as e:
            print(f"Traffic model inference error: {e}")
            return mock_traffic_detection(img)

        names = self._class_names()
        riders = []
        if det is not None and len(det):
            for *xyxy, conf, cls in det:
                cn = names[int(cls)]
                if cn == "Rider":
                    riders.append({"bbox": [int(x.item()) for x in xyxy], "confidence": float(conf.item())})

        results = []
        for rider in riders:
            rx1, ry1, rx2, ry2 = rider["bbox"]
            pad = 10
            ry1c = max(0, ry1 - pad)
            ry2c = min(img.shape[0], ry2 + pad)
            rx1c = max(0, rx1 - pad)
            rx2c = min(img.shape[1], rx2 + pad)
            rider_crop = img[ry1c:ry2c, rx1c:rx2c]
            if rider_crop.size == 0:
                continue

            crop_det = self._infer(rider_crop, size=CROP_IMG_SIZE)
            sub_detections = []
            lp_bbox = None
            if crop_det is not None and len(crop_det):
                for *cxyxy, cconf, ccls in crop_det:
                    cn = names[int(ccls)]
                    sub_detections.append({"class": cn, "confidence": float(cconf.item())})
                    if cn == "LP" and cconf.item() >= 0.4:
                        lp_bbox = [int(x.item()) for x in cxyxy]

            has_helmet = any(d["class"] == "Helmet" for d in sub_detections)
            has_no_helmet = any(d["class"] == "No Helmet" for d in sub_detections)

            if has_no_helmet:
                v_type = "NO_HELMET"
                v_conf = max(d["confidence"] for d in sub_detections if d["class"] == "No Helmet")
            elif has_helmet:
                v_type = "CORRECT"
                v_conf = max(d["confidence"] for d in sub_detections if d["class"] == "Helmet")
            else:
                continue

            detection = {
                "violation_type": v_type,
                "confidence": round(float(v_conf), 4),
                "bbox": rider["bbox"],
                "sub_detections": sub_detections,
            }
            if lp_bbox is not None:
                lx1, ly1, lx2, ly2 = lp_bbox
                lp_image = rider_crop[ly1:ly2, lx1:lx2]
                if lp_image.size > 0:
                    detection["lp_image"] = lp_image
                detection["lp_bbox_in_rider"] = lp_bbox
            results.append(detection)
        return results


def mock_traffic_detection(frame):
    h, w = frame.shape[:2]
    detections = []

    if np.random.random() > 0.5:
        conf = np.random.uniform(0.6, 0.98)
        cx, cy = int(w * 0.5), int(h * 0.4)
        bw, bh = np.random.randint(40, 120), np.random.randint(60, 180)
        x1, y1 = max(0, cx - bw // 2), max(0, cy - bh // 2)
        x2, y2 = min(w, cx + bw // 2), min(h, cy + bh // 2)

        sub_detections = []
        if np.random.random() > 0.4:
            sub_detections.append({"class": "Helmet", "confidence": float(np.random.uniform(0.7, 0.95))})
        else:
            sub_detections.append({"class": "No Helmet", "confidence": float(np.random.uniform(0.7, 0.95))})
        if np.random.random() > 0.6:
            sub_detections.append({"class": "LP", "confidence": float(np.random.uniform(0.6, 0.9))})

        has_helmet = any(d["class"] == "Helmet" for d in sub_detections)
        has_no_helmet = any(d["class"] == "No Helmet" for d in sub_detections)

        if has_no_helmet:
            violation_type = "NO_HELMET"
            v_conf = max(d["confidence"] for d in sub_detections if d["class"] == "No Helmet")
        elif has_helmet:
            violation_type = "CORRECT"
            v_conf = max(d["confidence"] for d in sub_detections if d["class"] == "Helmet")
        else:
            return []
        if violation_type == "CORRECT":
            return []

        detections.append({
            "violation_type": violation_type,
            "confidence": round(float(v_conf), 4),
            "bbox": [int(x1), int(y1), int(x2), int(y2)],
            "sub_detections": sub_detections,
        })
    return detections