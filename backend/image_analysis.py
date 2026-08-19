import base64
import io
import os

from PIL import Image, ImageOps, UnidentifiedImageError

from backend.color_math import similarity_score
from backend.color_region_segmentation import segment_largest_color_region
from backend.sam_segmentation import segment_best_object as sam_segment
from backend.yolo_segmentation import segment_best_object as yolo_segment


MAX_UPLOAD_BYTES = 12 * 1024 * 1024


def analyze_photo(file_storage, target):
    raw = file_storage.read(MAX_UPLOAD_BYTES + 1)
    if not raw:
        raise ValueError("사진을 선택해주세요.")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise ValueError("사진은 12MB 이하만 사용할 수 있습니다.")

    try:
        with Image.open(io.BytesIO(raw)) as source:
            image = ImageOps.exif_transpose(source).convert("RGB")
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("읽을 수 없는 이미지입니다.") from exc

    # SAM 입력과 결과 전송량을 줄이기 위한 게임용 최대 크기다.
    image.thumbnail((900, 900))
    outlined, representative, area_ratio, match_found, device = yolo_segment(image, target)
    method = f"YOLO11n-seg ({device}) + LAB Delta E"
    selection_type = "object"
    if not match_found:
        outlined, representative, area_ratio, match_found = segment_largest_color_region(image, target)
        method = f"LAB color-region fallback ({device})"
        selection_type = "region"
    if not match_found and should_use_sam(device):
        outlined, representative, area_ratio, match_found = sam_segment(image, target)
        method = f"SlimSAM fallback ({device}) + LAB Delta E"
        selection_type = "object"

    if representative is None:
        color_score = 0.0
    else:
        color_score = similarity_score(target, representative)

    output = io.BytesIO()
    outlined.save(output, "JPEG", quality=88, optimize=True)
    preview = "data:image/jpeg;base64," + base64.b64encode(output.getvalue()).decode("ascii")
    return {
        "preview": preview,
        "representative": color_hex(representative) if representative is not None else None,
        "color_score": color_score,
        "match_ratio": round(area_ratio * 100, 1),
        "match_found": match_found,
        "analysis_method": method,
        "selection_type": selection_type if match_found else None,
    }


def color_hex(rgb):
    return "#{:02X}{:02X}{:02X}".format(*(int(value) for value in rgb))


def should_use_sam(device):
    setting = os.environ.get("COLORHUNT_SAM_FALLBACK", "auto").lower()
    return setting == "1" or (setting == "auto" and device != "cpu")
