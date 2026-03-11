from enum import Enum
from typing import Any


class ErrorCode(str, Enum):
    """애플리케이션 에러 코드."""

    # ── 공통 ──────────────────────────────────────────────────────────────────
    NOT_FOUND = "NOT_FOUND"
    VALIDATION_ERROR = "VALIDATION_ERROR"

    # ── 커스텀 필터 ──────────────────────────────────────────────────────────
    CUSTOM_FILTER_NOT_FOUND = "CUSTOM_FILTER_NOT_FOUND"
    CUSTOM_FILTER_EXEC_ERROR = "CUSTOM_FILTER_EXEC_ERROR"
    CUSTOM_FILTER_NO_RESULT = "CUSTOM_FILTER_NO_RESULT"
    CUSTOM_FILTER_INVALID_NDIM = "CUSTOM_FILTER_INVALID_NDIM"
    CUSTOM_FILTER_INVALID_CHANNELS = "CUSTOM_FILTER_INVALID_CHANNELS"
    CUSTOM_FILTER_INVALID_DTYPE = "CUSTOM_FILTER_INVALID_DTYPE"

    # ── 이미지 처리 ──────────────────────────────────────────────────────────
    UNSUPPORTED_PRC_TYPE = "UNSUPPORTED_PRC_TYPE"
    INVALID_IMAGE = "INVALID_IMAGE"
    ENCODE_FAILED = "ENCODE_FAILED"


class AppError(Exception):
    """애플리케이션 표준 에러."""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        status_code: int = 400,
        detail: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        self.detail = detail or {}
        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "code": self.code.value,
            "message": self.message,
        }
        if self.detail:
            result["detail"] = self.detail
        return result
