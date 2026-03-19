import math
from typing import Any

import cv2
import numpy as np

from app.core.errors import AppError, ErrorCode
from app.repos.custom_filters_repo import (
    insert_custom_filter,
    get_custom_filter_list,
    get_custom_filter_by_id,
    update_custom_filter,
    delete_custom_filter,
)

# ── 샌드박스 실행 엔진 ────────────────────────────────────────────────────────

ALLOWED_GLOBALS: dict[str, Any] = {
    "__builtins__": {},
    "np": np,
    "cv2": cv2,
    "math": math,
}


def execute_custom_filter(
    code: str,
    image: np.ndarray,
    params: dict[str, Any],
) -> np.ndarray:
    """커스텀 필터 코드를 샌드박스 환경에서 실행한다."""
    local_vars: dict[str, Any] = {
        "image": image.copy(),
        "params": params,
        "result": None,
    }
    try:
        exec(code, ALLOWED_GLOBALS, local_vars)  # noqa: S102
    except Exception as e:
        raise AppError(
            code=ErrorCode.CUSTOM_FILTER_EXEC_ERROR,
            message=f"커스텀 필터 코드 실행 중 오류: {e}",
            detail={"error_type": type(e).__name__, "error": str(e)},
        ) from e

    result: np.ndarray = local_vars.get("result")  # type: ignore[assignment]
    _validate_result(result)
    return result


def _validate_result(result: Any) -> None:
    if not isinstance(result, np.ndarray):
        raise AppError(
            code=ErrorCode.CUSTOM_FILTER_NO_RESULT,
            message="result가 np.ndarray가 아닙니다.",
            detail={"actual_type": type(result).__name__},
        )
    if result.ndim not in (2, 3):
        raise AppError(
            code=ErrorCode.CUSTOM_FILTER_INVALID_NDIM,
            message=f"result shape이 이미지 형식이 아닙니다: ndim={result.ndim} (2D 또는 3D 필요)",
            detail={"ndim": result.ndim, "shape": list(result.shape)},
        )
    if result.ndim == 3 and result.shape[2] not in (1, 3, 4):
        raise AppError(
            code=ErrorCode.CUSTOM_FILTER_INVALID_CHANNELS,
            message=f"result 채널 수가 유효하지 않습니다: {result.shape[2]} (1, 3, 4만 허용)",
            detail={"channels": result.shape[2], "shape": list(result.shape)},
        )
    if result.dtype != np.uint8:
        raise AppError(
            code=ErrorCode.CUSTOM_FILTER_INVALID_DTYPE,
            message=f"result dtype이 uint8이 아닙니다: {result.dtype}",
            detail={"expected": "uint8", "actual": str(result.dtype)},
        )


# ── CRUD ──────────────────────────────────────────────────────────────────────


def create_custom_filter(
    *,
    nm: str,
    description: str,
    code: str,
    params: list[dict[str, Any]],
) -> dict[str, Any]:
    return insert_custom_filter(
        nm=nm, description=description, code=code, params=params,
    )


def list_custom_filters() -> list[dict[str, Any]]:
    return get_custom_filter_list()


def get_custom_filter(filter_id: str) -> dict[str, Any] | None:
    return get_custom_filter_by_id(filter_id)


def modify_custom_filter(
    filter_id: str,
    *,
    nm: str | None = None,
    description: str | None = None,
    code: str | None = None,
    params: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    return update_custom_filter(
        filter_id, nm=nm, description=description, code=code, params=params,
    )


def remove_custom_filter(filter_id: str) -> bool:
    return delete_custom_filter(filter_id)


def test_custom_filter(
    code: str,
    image_bytes: bytes,
    params: dict[str, Any],
) -> bytes:
    """코드를 직접 테스트 실행하고 결과 이미지 바이트를 반환한다."""
    if not image_bytes:
        raise AppError(
            code=ErrorCode.INVALID_IMAGE,
            message="이미지 데이터가 비어 있습니다.",
        )

    image_array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    if image is None:
        raise AppError(
            code=ErrorCode.INVALID_IMAGE,
            message="유효하지 않은 이미지 데이터입니다.",
        )

    processed = execute_custom_filter(code, image, params)

    success, encoded = cv2.imencode(".png", processed)
    if not success:
        raise AppError(
            code=ErrorCode.ENCODE_FAILED,
            message="처리 결과 이미지 인코딩에 실패했습니다.",
            status_code=500,
        )

    return encoded.tobytes()
