from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from typing import Literal


def to_camel(value: str) -> str:
    """snake_case -> camel_case
    """
    
    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


PrcType = Literal[
    # Edge Detection
    "sobel", "prewitt", "laplacian", "canny", "roberts",
    # Blurring
    "gaussian", "blur", "gaussianBlur", "medianBlur", "bilateralFilter", "boxFilter",
    # Contour Detection
    "findContour", "convexHull", "boundingBox",
    # Brightness
    "plus", "minus", "gamma", "histogramEqualization",
    # Thresholding
    "binary", "inverse", "tozero", "tozeroInverse", "truncate", "otsu", "adaptive",
    # Morphological
    "erosion", "dilation", "opening", "closing",
    # Custom
    "custom",
]


class ImgProcessingForm(BaseModel):
    prc_type: PrcType = Field(..., alias="prcType", description="적용할 이미지 처리 종류")
    kernel_size: int | None = Field(None, alias="kernelSize", ge=1, description="커널 크기 (홀수). None이면 처리 종류별 기본값 사용")


class FileSaveOptions(CamelModel):
    model_config = ConfigDict(extra="allow")  # 정의되지 않은 추가 키 허용
    prc_type: PrcType | None = Field(None, description="저장 시 적용된 이미지 처리 종류")


class FileSaveResponse(CamelModel):
    id: str = Field(..., description="파일 고유 식별자 (UUID)")
    origin_nm: str = Field(..., description="업로드 원본 파일명")
    nm: str = Field(..., description="서버 저장 파일명 (UUID 기반)")
    path: str = Field(..., description="서버 내 파일 경로 (uploads/ 기준)")
    mime_type: str = Field(..., description="파일 MIME 타입 (image/png, image/jpeg)")
    size_bytes: int = Field(..., ge=0, description="파일 크기 (bytes)")
    uploaded_at: datetime = Field(..., description="업로드 완료 시각 (UTC)")
    options: FileSaveOptions = Field(..., description="처리 시 적용된 옵션")


class TFile(CamelModel):
    id: str = Field(..., description="파일 고유 식별자 (UUID)")
    origin_nm: str = Field(..., description="업로드 원본 파일명")
    nm: str = Field(..., description="서버 저장 파일명 (UUID 기반)")
    path: str = Field(..., description="서버 내 파일 경로 (uploads/ 기준)")
    mime_type: str = Field(..., description="파일 MIME 타입 (image/png, image/jpeg)")
    size_bytes: int = Field(..., ge=0, description="파일 크기 (bytes)")
    uploaded_at: datetime = Field(..., description="업로드 완료 시각 (UTC)")
    options: FileSaveOptions = Field(..., description="처리 시 적용된 옵션")
    thumbnail_url: str | None = Field(None, description="썸네일 base64 data URL")


class FileUploadResponse(CamelModel):
    id: str = Field(..., description="파일 고유 식별자 (UUID)")
    origin_nm: str = Field(..., description="업로드 원본 파일명")
    nm: str = Field(..., description="서버 저장 파일명 (UUID 기반)")
    path: str = Field(..., description="서버 내 파일 경로 (uploads/ 기준)")
    mime_type: str = Field(..., description="파일 MIME 타입 (image/png, image/jpeg)")
    size_bytes: int = Field(..., ge=0, description="파일 크기 (bytes)")
    uploaded_at: datetime = Field(..., description="업로드 완료 시각 (UTC)")


class TreeNodeResultResponse(CamelModel):
    node_id: str = Field(..., description="노드 고유 식별자")
    image_url: str = Field(..., description="처리 결과 이미지 URL (썸네일 base64 data URL)")
    execution_ms: float = Field(..., description="해당 노드 처리 시간 (ms)")


class DziResponse(CamelModel):
    dzi_url: str | None = Field(None, description="DZI 타일 URL (고해상도일 때)")
    image_url: str | None = Field(None, description="원본 이미지 URL (저해상도일 때)")


class TreeBatchResponse(CamelModel):
    total_execution_ms: float = Field(..., description="전체 트리 처리 시간 (ms)")
    results: list[TreeNodeResultResponse] = Field(..., description="노드별 처리 결과")


class FileItem(CamelModel):
    id: str = Field(..., description="파일 고유 식별자 (UUID)")
    origin_nm: str = Field(..., description="업로드 원본 파일명")
    nm: str = Field(..., description="서버 저장 파일명 (UUID 기반)")
    path: str = Field(..., description="서버 내 파일 경로 (uploads/ 기준)")
    mime_type: str = Field(..., description="파일 MIME 타입")
    size_bytes: int = Field(..., ge=0, description="파일 크기 (bytes)")
    uploaded_at: datetime = Field(..., description="업로드 완료 시각 (UTC)")
    options: dict = Field(default_factory=dict, description="파일 관련 추가 메타데이터")


class FileListResponse(CamelModel):
    items: list[TFile] = Field(..., description="파일 목록")
    has_more: bool = Field(..., description="다음 페이지 존재 여부")
    next_cursor_uploaded_at: datetime | None = Field(None, description="다음 커서 기준 업로드 시각")
    next_cursor_id: str | None = Field(None, description="다음 커서 파일 ID")


class FileItemListResponse(CamelModel):
    items: list[FileItem] = Field(..., description="파일 목록")
    has_more: bool = Field(..., description="다음 페이지 존재 여부")
    next_cursor_uploaded_at: datetime | None = Field(None, description="다음 커서 기준 업로드 시각")
    next_cursor_id: str | None = Field(None, description="다음 커서 파일 ID")


class FileRenameRequest(CamelModel):
    origin_nm: str = Field(..., min_length=1, max_length=255, description="변경할 파일명")
