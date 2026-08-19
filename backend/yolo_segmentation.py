import queue
import threading
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageChops, ImageFilter

from backend.color_math import delta_e
from backend.sam_segmentation import closest_dominant_color, visible_outline_color


MODEL_PATH = Path(__file__).with_name("yolo11n-seg.pt")
_model = None
_model_lock = threading.Lock()
_batcher = None
_batcher_lock = threading.Lock()
MAX_BATCH_SIZE = 20
BATCH_WINDOW_SECONDS = 0.08


def segment_best_object(image, target):
    """YOLO11 nano가 찾은 물체 중 목표색과 가장 가까운 하나를 반환한다."""
    return _get_batcher().submit(image, target)


def _select_best_object(image, target, result, device):
    image_array = np.asarray(image)

    if result.masks is None or result.boxes is None:
        return image.copy(), None, 0, False, device

    width, height = image.size
    total_pixels = width * height
    candidates = []
    classes = result.boxes.cls.cpu().numpy().astype(int)
    confidences = result.boxes.conf.cpu().numpy()

    for index, polygon in enumerate(result.masks.xy):
        class_name = result.names[int(classes[index])]
        if class_name == "person" or len(polygon) < 3:
            continue
        mask = np.zeros((height, width), dtype=np.uint8)
        cv2.fillPoly(mask, [np.asarray(polygon, dtype=np.int32)], 255)
        selected = mask.astype(bool)
        area = int(selected.sum())
        area_ratio = area / total_pixels
        if area_ratio < 0.01 or area_ratio > 0.80:
            continue

        # 경계의 배경 혼입을 줄이기 위해 마스크 안쪽 색상을 사용한다.
        kernel_size = max(3, int(min(width, height) * 0.012) | 1)
        kernel = np.ones((kernel_size, kernel_size), np.uint8)
        inner = cv2.erode(mask, kernel, iterations=1).astype(bool)
        if inner.sum() < max(20, area * 0.35):
            inner = selected
        representative, color_distance, coverage = closest_dominant_color(image_array[inner], target)
        confidence = float(confidences[index])
        rank = color_distance - coverage * 8 - confidence * 2
        candidates.append(
            (rank, color_distance, -coverage, -confidence, selected, representative, area_ratio, class_name)
        )

    if not candidates:
        return image.copy(), None, 0, False, device

    _, color_distance, _, _, best_mask, representative, area_ratio, _ = min(
        candidates, key=lambda candidate: candidate[:4]
    )
    if color_distance > 38:
        return image.copy(), representative, 0, False, device

    mask_image = Image.fromarray(best_mask.astype(np.uint8) * 255, mode="L")
    outside = mask_image.filter(ImageFilter.MaxFilter(11))
    inside = mask_image.filter(ImageFilter.MinFilter(5))
    edge = ImageChops.subtract(outside, inside)
    result_image = image.copy()
    outline = Image.new("RGB", image.size, visible_outline_color(target))
    result_image.paste(outline, mask=edge)
    return result_image, representative, area_ratio, True, device


class YoloBatcher:
    """짧은 시간에 들어온 최대 20장의 요청을 한 번의 YOLO 호출로 묶는다."""

    def __init__(self):
        self.model, self.device = _get_model()
        self.requests = queue.Queue()
        threading.Thread(target=self._run, daemon=True, name="yolo-batch-worker").start()

    def submit(self, image, target):
        finished = threading.Event()
        holder = {}
        self.requests.put((image, target, finished, holder))
        finished.wait()
        if "error" in holder:
            raise RuntimeError(f"YOLO 분석 실패: {holder['error']}") from holder["error"]
        return holder["result"]

    def _run(self):
        while True:
            batch = [self.requests.get()]
            deadline = time.monotonic() + BATCH_WINDOW_SECONDS
            while len(batch) < MAX_BATCH_SIZE:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                try:
                    batch.append(self.requests.get(timeout=remaining))
                except queue.Empty:
                    break
            try:
                images = [np.asarray(item[0]) for item in batch]
                results = self.model.predict(
                    source=images,
                    imgsz=640,
                    conf=0.20,
                    iou=0.65,
                    device=self.device,
                    batch=len(images),
                    verbose=False,
                )
                for item, result in zip(batch, results):
                    image, target, _, holder = item
                    holder["result"] = _select_best_object(image, target, result, self.device)
            except Exception as exc:
                for _, _, _, holder in batch:
                    holder["error"] = exc
            finally:
                for _, _, finished, _ in batch:
                    finished.set()


def _get_batcher():
    global _batcher
    if _batcher is not None:
        return _batcher
    with _batcher_lock:
        if _batcher is None:
            _batcher = YoloBatcher()
    return _batcher


def warmup():
    """서버 시작 시 모델을 미리 로드해 첫 제출 지연을 없앤다."""
    _get_batcher()


def _get_model():
    global _model
    import torch
    from ultralytics import YOLO

    device = 0 if torch.cuda.is_available() else "cpu"
    if _model is not None:
        return _model, device
    with _model_lock:
        if _model is None:
            _model = YOLO(MODEL_PATH)
            # 첫 실제 제출이 느려지지 않도록 작은 더미 입력으로 워밍업한다.
            _model.predict(np.zeros((320, 320, 3), dtype=np.uint8), imgsz=640, device=device, verbose=False)
    return _model, device
