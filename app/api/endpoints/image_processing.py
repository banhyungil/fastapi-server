# 외부 패키지는 패키지명으로 import
from io import BytesIO
import logging
from pathlib import Path
from typing import Annotated
from uuid import uuid4
from uuid import UUID
from datetime import datetime
import time 

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse

# 절대 import
from app.schemas.file import TFile, FileListResponse, FileSaveResponse, FileSaveOptions, PrcType
from app.services.file_service import insert_file, list_files
from app.services.image_processing_service import process_image

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/image-processing", tags=["img-processing"], response_model=FileListResponse)
async def get_saved_images(
    limit: Annotated[int, Query(ge=1, le=100, description="반환할 최대 항목 수")] = 20,
    cursor_uploaded_at: Annotated[datetime | None, Query(alias="cursorUploadedAt", description="커서 기준 업로드 시각 (cursorId와 함께 제공)")] = None,
    cursor_id: Annotated[UUID | None, Query(alias="cursorId", description="커서 기준 파일 ID (cursorUploadedAt와 함께 제공)")] = None,
) -> FileListResponse:
    """처리 이미지 조회"""

    if (cursor_uploaded_at is None) != (cursor_id is None):
        raise HTTPException(status_code=400, detail="cursorUploadedAt and cursorId must be provided together")

    page = list_files(
        limit=limit,
        cursor_uploaded_at=cursor_uploaded_at,
        cursor_id=cursor_id,
    )

    return FileListResponse(
        # model_validate 사용 시 중첩 dict구조도 변환한다
        items=[TFile.model_validate(item) for item in page["items"]],
        has_more=page["has_more"],
        next_cursor_uploaded_at=page["next_cursor_uploaded_at"],
        next_cursor_id=page["next_cursor_id"],
    )

@router.post("/image-processing", tags=["img-processing"])
async def img_processing(
    file: Annotated[UploadFile, File(description="처리할 원본 이미지 파일")],
    prc_type: Annotated[PrcType, Form(alias="prcType", description="적용할 이미지 처리 종류")],
    kernel_size: Annotated[int | None, Form(alias="kernelSize", description="커널 크기 (홀수). None이면 처리 종류별 기본값 사용")] = None,
) -> StreamingResponse:
    """이미지 처리"""

    uploaded_file_bytes = await file.read()

    try:
        start = time.perf_counter()
        processed_image_bytes = process_image(
            prc_type=prc_type,
            image_bytes=uploaded_file_bytes,
            kernel_size=kernel_size,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return StreamingResponse(
        BytesIO(processed_image_bytes), 
        media_type="image/png",
        headers={"X-Process-Time-Ms": f"{elapsed_ms:.2f}"}
        )


@router.post("/image-processing/save", tags=["img-processing"], response_model=FileSaveResponse)
async def img_processing_save(
    blob: Annotated[UploadFile, File(description="저장할 처리 완료 이미지 (image/png 또는 image/jpeg)")],
    prc_type: Annotated[PrcType, Form(alias="prcType", description="이미지에 적용된 처리 종류")],
    prc_ms: Annotated[float, Form(alias="prcMs", description="처리시간")]
) -> FileSaveResponse:
    """처리 이미지 저장"""

    # Python: 연산자 오버로딩
    # Path / "문자열"이면 Path.__truediv__()가 호출되어 경로 결합 연산자로 작동
    base = Path("uploads") / datetime.now().strftime("%Y-%m-%d")
    base.mkdir(parents=True, exist_ok=True)

    data = await blob.read()
    if blob.content_type not in ("image/png", "image/jpeg"):
        raise HTTPException(400, "unsupported content type")

    #### 파일쓰기 ####
    ext = ".png" if blob.content_type == "image/png" else ".jpg"
    saved_name = f"{uuid4().hex}{ext}"
    saved = base / saved_name
    saved.write_bytes(data)

    origin_nm = blob.filename or saved_name
    saved_path = str(saved).replace("\\", "/")

    #### DB 저장 ####
    try:
        inserted = insert_file(
            origin_nm=origin_nm,
            nm=saved_name,
            path=saved_path,
            mime_type=blob.content_type,
            size_bytes=len(data),
            options={"prcType": prc_type, "prcMs": prc_ms},
        )
    except Exception as exc:
        logger.exception("failed to persist file metadata")
        if saved.exists():
            saved.unlink()
        raise HTTPException(status_code=500, detail="failed to persist file metadata") from exc

    #### 응답 ####
    return FileSaveResponse(
        id=inserted["id"],
        origin_nm=origin_nm,
        nm=saved_name,
        path=saved_path,
        mime_type=blob.content_type,
        size_bytes=len(data),
        uploaded_at=inserted["uploaded_at"],
        options=FileSaveOptions(prc_type=prc_type),
    )
