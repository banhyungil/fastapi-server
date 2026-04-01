"""Crop 기반 이미지 미리보기 서비스."""

import time as _time
from pathlib import Path
from typing import Any
from uuid import uuid4

import cv2
import numpy as np

from app.schemas.files_schema import FilterType
from app.schemas.image_processing_schema import PARAM_MODELS
from app.services.cache import CACHE_DIR
from app.services.operations import OPERATIONS
from app.services.dzi import _process_chain_to_node

PREVIEW_MIN_CROP_PIXELS = 2_500        # 총 픽셀 수 최소 (50x50)
PREVIEW_MAX_CROP_PIXELS = 16_000_000   # 총 픽셀 수 최대 (4000x4000)


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

    # viewport 크기 검증 (총 픽셀 수 기준)
    vw, vh = viewport["w"], viewport["h"]
    pixels = vw * vh
    if pixels < PREVIEW_MIN_CROP_PIXELS:
        raise ValueError(f"crop size too small: {vw}x{vh} = {pixels}px (min {PREVIEW_MIN_CROP_PIXELS})")
    if pixels > PREVIEW_MAX_CROP_PIXELS:
        raise ValueError(f"crop size too large: {vw}x{vh} = {pixels}px (max {PREVIEW_MAX_CROP_PIXELS})")

    # 노드 이미지 생성
    if node_steps:
        node_image = _process_chain_to_node(file_path, node_steps, node_id)
    else:
        node_image = cv2.imread(file_path, cv2.IMREAD_COLOR)
        if node_image is None:
            raise ValueError(f"failed to read image: {file_path}")

    h_img, w_img = node_image.shape[:2]

    # 전체 이미지 crop인지 판별
    is_full = (
        viewport["x"] <= 0
        and viewport["y"] <= 0
        and viewport["w"] >= w_img
        and viewport["h"] >= h_img
    )

    crop_id = uuid4().hex
    preview_dir = CACHE_DIR / file_id / "preview"
    preview_dir.mkdir(parents=True, exist_ok=True)

    if is_full:
        # 전체 이미지 — crop 불필요, 원본(노드 이미지)을 그대로 캐시
        crop_path = preview_dir / f"{crop_id}.png"
        cv2.imwrite(str(crop_path), node_image)

        # 노드 이미지 URL은 원본 파일 경로 사용 (steps 없으면) 또는 캐시 파일
        node_image_url = f"/{str(crop_path).replace(chr(92), '/')}"

        return PreviewCropResult(
            crop_id=crop_id,
            node_image_url=node_image_url,
            width=w_img,
            height=h_img,
        )

    # viewport + padding으로 crop (clamp)
    x1 = max(0, viewport["x"] - padding)
    y1 = max(0, viewport["y"] - padding)
    x2 = min(w_img, viewport["x"] + viewport["w"] + padding)
    y2 = min(h_img, viewport["y"] + viewport["h"] + padding)
    cropped = node_image[y1:y2, x1:x2]

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


class IntermediateResult:
    __slots__ = ("filter_type", "image_bytes", "execution_ms")

    def __init__(self, filter_type: str, image_bytes: bytes, execution_ms: float = 0) -> None:
        self.filter_type = filter_type
        self.image_bytes = image_bytes
        self.execution_ms = execution_ms


def _remove_padding(
    image: np.ndarray,
    cropped: np.ndarray,
    viewport: dict[str, int],
    padding: int,
) -> np.ndarray:
    """crop 이미지에서 padding 영역을 제거한다."""
    h_crop, w_crop = cropped.shape[:2]
    px = min(padding, (w_crop - viewport["w"]) // 2) if w_crop > viewport["w"] else 0
    py = min(padding, (h_crop - viewport["h"]) // 2) if h_crop > viewport["h"] else 0
    vw = min(viewport["w"], image.shape[1] - px)
    vh = min(viewport["h"], image.shape[0] - py)
    return image[py : py + vh, px : px + vw]


def _load_crop(file_id: str, crop_id: str) -> np.ndarray:
    """캐시된 crop 이미지를 로드한다."""
    crop_path = CACHE_DIR / file_id / "preview" / f"{crop_id}.png"
    if not crop_path.exists():
        raise ValueError(f"preview crop not found: {crop_id}")

    cropped = cv2.imread(str(crop_path), cv2.IMREAD_COLOR)
    if cropped is None:
        raise ValueError(f"failed to read crop image: {crop_id}")
    return cropped


def _apply_steps(image: np.ndarray, temp_steps: list[dict[str, Any]]) -> np.ndarray:
    """이미지에 temp_steps를 순차 적용한다."""
    result = image.copy()
    for step in temp_steps:
        filter_type: FilterType = step["filterType"]
        parameters: dict[str, Any] = step.get("parameters", {})

        op = OPERATIONS.get(filter_type)
        if op is None:
            raise ValueError(f"unsupported filterType: {filter_type}")

        param_cls = PARAM_MODELS[filter_type]
        params = param_cls.model_validate(parameters)
        result = op(result, params)
    return result


def apply_preview_filter(
    file_id: str,
    crop_id: str,
    temp_steps: list[dict[str, Any]],
    viewport: dict[str, int],
    padding: int = 50,
) -> bytes:
    """캐시된 crop 이미지에 tempSteps를 적용하여 최종 결과를 반환한다."""

    cropped = _load_crop(file_id, crop_id)
    result = _apply_steps(cropped, temp_steps)
    result = _remove_padding(result, cropped, viewport, padding)

    success, encoded = cv2.imencode(".png", result)
    if not success:
        raise RuntimeError("failed to encode preview result")

    return encoded.tobytes()


def apply_preview_filter_all(
    file_id: str,
    crop_id: str,
    temp_steps: list[dict[str, Any]],
    viewport: dict[str, int],
    padding: int = 50,
) -> list[IntermediateResult]:
    """캐시된 crop 이미지에 tempSteps를 적용하고 각 step별 중간 결과를 반환한다."""

    cropped = _load_crop(file_id, crop_id)
    intermediates: list[IntermediateResult] = []
    result = cropped.copy()

    for step in temp_steps:
        filter_type: FilterType = step["filterType"]
        parameters: dict[str, Any] = step.get("parameters", {})

        op = OPERATIONS.get(filter_type)
        if op is None:
            raise ValueError(f"unsupported filterType: {filter_type}")

        param_cls = PARAM_MODELS[filter_type]
        params = param_cls.model_validate(parameters)

        step_start = _time.perf_counter()
        result = op(result, params)
        step_ms = (_time.perf_counter() - step_start) * 1000

        trimmed = _remove_padding(result, cropped, viewport, padding)
        success, encoded = cv2.imencode(".png", trimmed)
        if success:
            intermediates.append(IntermediateResult(filter_type, encoded.tobytes(), round(step_ms, 2)))

    return intermediates


def delete_preview_crop(file_id: str, crop_id: str) -> None:
    """캐시된 preview crop 파일을 삭제한다."""
    preview_dir = CACHE_DIR / file_id / "preview"
    for path in preview_dir.glob(f"{crop_id}*"):
        path.unlink(missing_ok=True)
