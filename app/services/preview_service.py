"""이미지 미리보기 (crop + 필터 적용) 서비스."""

from pathlib import Path
from typing import Any
from uuid import uuid4

import cv2
import numpy as np

from app.schemas.file import PrcType
from app.schemas.image_processing import PARAM_MODELS
from app.services.image_processing_service import (
    CACHE_DIR,
    OPERATIONS,
    _process_chain_to_node,
)

PREVIEW_MAX_CROP = 2000  # px — crop 최대 크기 제한


class PreviewCropResult:
    __slots__ = ("crop_id", "node_image_url", "width", "height")

    def __init__(self, *, crop_id: str, node_image_url: str, width: int, height: int) -> None:
        self.crop_id = crop_id
        self.node_image_url = node_image_url
        self.width = width
        self.height = height


def create_preview_crop(
    file_path: str,
    node_steps: list[dict[str, Any]],
    node_id: str,
    viewport: dict[str, int],
    *,
    file_id: str,
    padding: int = 50,
) -> PreviewCropResult:
    """노드 이미지를 생성하고 viewport 영역을 crop하여 캐시한다."""

    # 노드 이미지 생성
    if node_steps:
        node_image = _process_chain_to_node(file_path, node_steps, node_id)
    else:
        node_image = cv2.imread(file_path, cv2.IMREAD_COLOR)
        if node_image is None:
            raise ValueError(f"failed to read image: {file_path}")

    h_img, w_img = node_image.shape[:2]

    # viewport + padding으로 crop (clamp)
    x1 = max(0, viewport["x"] - padding)
    y1 = max(0, viewport["y"] - padding)
    x2 = min(w_img, viewport["x"] + viewport["w"] + padding)
    y2 = min(h_img, viewport["y"] + viewport["h"] + padding)
    cropped = node_image[y1:y2, x1:x2]

    # 캐시 디렉토리 생성
    preview_dir = CACHE_DIR / file_id / "preview"
    preview_dir.mkdir(parents=True, exist_ok=True)

    crop_id = uuid4().hex

    # padding 포함 crop 저장 (apply에서 사용)
    crop_path = preview_dir / f"{crop_id}.png"
    cv2.imwrite(str(crop_path), cropped)

    # padding 제거한 노드 이미지 crop 저장 (비교 표시용)
    px = viewport["x"] - x1
    py = viewport["y"] - y1
    vw = min(viewport["w"], cropped.shape[1] - px)
    vh = min(viewport["h"], cropped.shape[0] - py)
    node_crop = cropped[py : py + vh, px : px + vw]

    node_crop_path = preview_dir / f"{crop_id}_node.png"
    cv2.imwrite(str(node_crop_path), node_crop)

    node_image_url = f"/{str(node_crop_path).replace(chr(92), '/')}"

    return PreviewCropResult(
        crop_id=crop_id,
        node_image_url=node_image_url,
        width=vw,
        height=vh,
    )


def apply_preview_filter(
    file_id: str,
    crop_id: str,
    temp_steps: list[dict[str, Any]],
    viewport: dict[str, int],
    padding: int = 50,
) -> bytes:
    """캐시된 crop 이미지에 tempSteps를 적용하여 결과를 반환한다."""

    crop_path = CACHE_DIR / file_id / "preview" / f"{crop_id}.png"
    if not crop_path.exists():
        raise ValueError(f"preview crop not found: {crop_id}")

    cropped = cv2.imread(str(crop_path), cv2.IMREAD_COLOR)
    if cropped is None:
        raise ValueError(f"failed to read crop image: {crop_id}")

    # tempSteps 순차 적용
    result = cropped.copy()
    for step in temp_steps:
        prc_type: PrcType = step["prcType"]
        parameters: dict[str, Any] = step.get("parameters", {})

        op = OPERATIONS.get(prc_type)
        if op is None:
            raise ValueError(f"unsupported prcType: {prc_type}")

        param_cls = PARAM_MODELS[prc_type]
        params = param_cls.model_validate(parameters)
        result = op(result, params)

    # padding 제거 — crop 시 실제 적용된 padding 계산
    h_crop, w_crop = cropped.shape[:2]
    px = min(padding, (w_crop - viewport["w"]) // 2) if w_crop > viewport["w"] else 0
    py = min(padding, (h_crop - viewport["h"]) // 2) if h_crop > viewport["h"] else 0
    vw = min(viewport["w"], result.shape[1] - px)
    vh = min(viewport["h"], result.shape[0] - py)
    result = result[py : py + vh, px : px + vw]

    success, encoded = cv2.imencode(".png", result)
    if not success:
        raise RuntimeError("failed to encode preview result")

    return encoded.tobytes()


def delete_preview_crop(file_id: str, crop_id: str) -> None:
    """캐시된 preview crop 파일을 삭제한다."""
    preview_dir = CACHE_DIR / file_id / "preview"
    for path in preview_dir.glob(f"{crop_id}*"):
        path.unlink(missing_ok=True)
