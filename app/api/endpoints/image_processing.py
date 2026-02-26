# 외부 패키지는 패키지명으로 import
from io import BytesIO
import logging
from pathlib import Path
from uuid import uuid4
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse

# 절대 import
from app.schemas.file import FileListItem, FileListResponse, FileSaveResponse
from app.services.file_service import insert_file, list_files
from app.services.image_processing_service import PrcType, process_image

router = APIRouter()
logger = logging.getLogger(__name__)

# 처리 이미지 조회
@router.get("/image-processing", tags=["img-processing"], response_model=FileListResponse)
async def get_saved_images(
    limit: int = Query(20, ge=1, le=100),
    cursor_uploaded_at: datetime | None = Query(None, alias="cursorUploadedAt"),
    cursor_id: UUID | None = Query(None, alias="cursorId"),
) -> FileListResponse:
    if (cursor_uploaded_at is None) != (cursor_id is None):
        raise HTTPException(status_code=400, detail="cursorUploadedAt and cursorId must be provided together")

    page = list_files(
        limit=limit,
        cursor_uploaded_at=cursor_uploaded_at,
        cursor_id=cursor_id,
    )

    return FileListResponse(
        items=[FileListItem(**item) for item in page["items"]],
        has_more=page["has_more"],
        next_cursor_uploaded_at=page["next_cursor_uploaded_at"],
        next_cursor_id=page["next_cursor_id"],
    )

# 이미지 처리
@router.post("/image-processing", tags=["img-processing"])
async def img_processing(
    file: UploadFile = File(...),
    prc_type: PrcType = Form(..., alias="prcType"),
    kernel_size: int | None = Form(None, alias="kernelSize"),
) -> StreamingResponse:
    uploaded_file_bytes = await file.read()

    try:
        processed_image_bytes = process_image(prc_type=prc_type, image_bytes=uploaded_file_bytes, kernel_size=kernel_size)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return StreamingResponse(BytesIO(processed_image_bytes), media_type="image/png")


# 처리 이미지 저장
@router.post("/image-processing/save", tags=["img-processing"], response_model=FileSaveResponse)
async def img_processing_save(blob: UploadFile = File(...), prc_type: str = Form(..., alias="prcType")) -> FileSaveResponse:
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
            options={"prcType": prc_type},
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
        options={"prcType": prc_type}
    )



