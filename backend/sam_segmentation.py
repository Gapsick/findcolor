import math
import threading

import numpy as np
from PIL import Image, ImageChops, ImageFilter
from backend.color_math import delta_e


MODEL_ID = "Zigeng/SlimSAM-uniform-50"
_model = None
_processor = None
_load_lock = threading.Lock()
_inference_lock = threading.Lock()


def segment_best_object(image, target):
    """SlimSAM 후보 중 목표색을 의미 있게 포함한 물체 하나를 선택한다."""
    model, processor = _get_model()
    width, height = image.size
    prompts = [
        [[width * x / 5, height * y / 5]]
        for y in range(1, 5)
        for x in range(1, 5)
    ]

    import torch

    inputs = processor(images=image, input_points=[prompts], return_tensors="pt")
    with _inference_lock, torch.inference_mode():
        outputs = model(**inputs, multimask_output=True)
    masks = processor.image_processor.post_process_masks(
        outputs.pred_masks,
        inputs["original_sizes"],
        inputs["reshaped_input_sizes"],
    )[0]
    quality_scores = outputs.iou_scores[0]

    image_array = np.asarray(image)
    candidates = []
    total_pixels = width * height
    for prompt_index in range(masks.shape[0]):
        for mask_index in range(masks.shape[1]):
            quality = float(quality_scores[prompt_index, mask_index])
            mask = masks[prompt_index, mask_index].cpu().numpy().astype(bool)
            area = int(mask.sum())
            area_ratio = area / total_pixels
            if quality < 0.62 or area_ratio < 0.015 or area_ratio > 0.85:
                continue

            representative, color_distance, coverage = closest_dominant_color(image_array[mask], target)
            # 색상 차이가 우선이고, 해당 색의 점유율과 SAM 품질을 보조 기준으로 사용한다.
            rank = color_distance - coverage * 8 - quality * 2
            candidates.append((rank, color_distance, -coverage, -quality, mask, representative, area_ratio))

    if not candidates:
        return image.copy(), None, 0, False

    _, color_distance, _, _, best_mask, representative, area_ratio = min(
        candidates, key=lambda candidate: candidate[:4]
    )
    # 너무 다른 물체를 억지로 선택하지 않는다.
    if color_distance > 38:
        return image.copy(), representative, 0, False

    mask_image = Image.fromarray(best_mask.astype(np.uint8) * 255, mode="L")
    outside = mask_image.filter(ImageFilter.MaxFilter(13))
    inside = mask_image.filter(ImageFilter.MinFilter(5))
    edge = ImageChops.subtract(outside, inside)
    result = image.copy()
    outline = Image.new("RGB", image.size, visible_outline_color(target))
    result.paste(outline, mask=edge)
    return result, representative, area_ratio, True


def closest_dominant_color(pixels, target):
    """물체 내부의 대표색 6개 중 목표색과 가장 가까운 충분한 크기의 색을 고른다."""
    if len(pixels) > 24000:
        step = max(1, len(pixels) // 24000)
        pixels = pixels[::step]
    strip = Image.fromarray(pixels.reshape(1, -1, 3).astype(np.uint8), "RGB")
    quantized = strip.quantize(colors=6, method=Image.Quantize.MEDIANCUT)
    counts = quantized.getcolors(maxcolors=6) or []
    palette = quantized.getpalette()
    minimum_count = max(1, int(len(pixels) * 0.06))
    choices = []
    for count, palette_index in counts:
        if count < minimum_count:
            continue
        offset = palette_index * 3
        color = tuple(palette[offset : offset + 3])
        distance = delta_e(color, target)
        choices.append((distance, -count, color, count / len(pixels)))
    if not choices:
        mean = tuple(np.mean(pixels, axis=0).round().astype(int))
        return mean, delta_e(mean, target), 1.0
    distance, _, color, coverage = min(choices)
    return color, distance, coverage


def visible_outline_color(target):
    luminance = 0.299 * target[0] + 0.587 * target[1] + 0.114 * target[2]
    return (255, 255, 255) if luminance < 115 else (20, 20, 20)


def _get_model():
    global _model, _processor
    if _model is not None:
        return _model, _processor
    with _load_lock:
        if _model is None:
            from transformers import SamModel, SamProcessor

            try:
                _processor = SamProcessor.from_pretrained(MODEL_ID, local_files_only=True)
                _model = SamModel.from_pretrained(MODEL_ID, local_files_only=True).eval()
            except OSError as exc:
                raise RuntimeError(
                    "SlimSAM 모델이 없습니다. README의 모델 설치 명령을 먼저 실행해주세요."
                ) from exc
    return _model, _processor
