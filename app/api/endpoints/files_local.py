"""로컬 파일 스캔 + 등록 엔드포인트."""

import logging

from fastapi import APIRouter, HTTPException

from app.schemas.files_local_schema import (
    LocalScanRequest,
    LocalScanResponse,
    LocalFileInfo,
    LocalRegisterRequest,
    LocalRegisterResponse,
)
from app.schemas.files_schema import FileUploadResponse
from app.services.files_local_service import scan_directory, register_local_files

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/files/local/scan", tags=["files-local"], response_model=LocalScanResponse)
async def scan_local_directory(body: LocalScanRequest) -> LocalScanResponse:
    """로컬 디렉토리를 스캔하여 이미지 파일 목록을 반환한다."""
    try:
        items = scan_directory(body.dir_path, recursive=body.recursive, use_thumbnail=body.use_thumbnail)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return LocalScanResponse(
        items=[LocalFileInfo.model_validate(item) for item in items],
    )


@router.post(
    "/files/local/register",
    tags=["files-local"],
    response_model=LocalRegisterResponse,
    status_code=201,
)
async def register_local(body: LocalRegisterRequest) -> LocalRegisterResponse:
    """선택한 로컬 파일들을 DB에 등록한다."""
    paths = [f.path for f in body.files]
    results = register_local_files(paths)

    return LocalRegisterResponse(
        items=[FileUploadResponse.model_validate(item) for item in results],
    )
