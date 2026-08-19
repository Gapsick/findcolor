import cv2
import numpy as np
from PIL import Image, ImageDraw

from backend.color_math import delta_e
LAB_THRESHOLD = 30.0


def segment_largest_color_region(image, target):
    """목표색과 가까운 픽셀이 연속된 가장 큰 영역 하나를 찾는다."""
    rgb = np.asarray(image)
    lab = cv2.cvtColor(rgb.astype(np.float32) / 255.0, cv2.COLOR_RGB2LAB)
    target_pixel = np.asarray(target, dtype=np.float32).reshape(1, 1, 3) / 255.0
    target_lab = cv2.cvtColor(target_pixel, cv2.COLOR_RGB2LAB)[0, 0]
    distance = np.linalg.norm(lab - target_lab, axis=2)
    mask = (distance <= LAB_THRESHOLD).astype(np.uint8) * 255

    height, width = mask.shape
    short_side = min(width, height)
    open_size = max(3, int(short_side * 0.008) | 1)
    close_size = max(5, int(short_side * 0.018) | 1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((open_size, open_size), np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((close_size, close_size), np.uint8))

    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    minimum_area = max(50, int(width * height * 0.008))
    candidates = []
    for label in range(1, count):
        area = int(stats[label, cv2.CC_STAT_AREA])
        if area < minimum_area:
            continue
        component = labels == label
        pixels = rgb[component]
        representative = tuple(np.median(pixels, axis=0).round().astype(int))
        color_distance = delta_e(representative, target)
        candidates.append((color_distance, -area, component, representative, area))

    if not candidates:
        return image.copy(), None, 0, False

    _, _, component, representative, area = min(candidates, key=lambda item: (item[0], item[1]))
    # 원본은 건드리지 않고 선택 영역을 감싸는 빨간 타원만 표시한다.
    ys, xs = np.where(component)
    padding = max(8, int(min(width, height) * 0.025))
    left = max(2, int(xs.min()) - padding)
    top = max(2, int(ys.min()) - padding)
    right = min(width - 3, int(xs.max()) + padding)
    bottom = min(height - 3, int(ys.max()) + padding)
    line_width = max(4, int(min(width, height) * 0.012))
    result = image.copy()
    draw = ImageDraw.Draw(result)
    # 바깥 흰 선은 가독성용이고, 안쪽 선은 실제 추출색과 정확히 같다.
    draw.ellipse(
        (left, top, right, bottom),
        outline=(255, 255, 255),
        width=line_width + 4,
    )
    draw.ellipse(
        (left, top, right, bottom),
        outline=tuple(int(channel) for channel in representative),
        width=line_width,
    )
    return result, representative, area / (width * height), True
