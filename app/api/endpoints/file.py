from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from app.schemas.file import FileItem, FileItemListResponse
from app.services.file_service import list_files

router = APIRouter()


@router.get("/files", tags=["file"], response_model=FileItemListResponse)
async def get_files(
    limit: Annotated[int, Query(ge=1, le=100, description="반환할 최대 항목 수")] = 20,
    mime_type: Annotated[str | None, Query(alias="mimeType", description="MIME 타입 필터 (예: image/png, image/*)")] = None,
    cursor_uploaded_at: Annotated[datetime | None, Query(alias="cursorUploadedAt", description="커서 기준 업로드 시각")] = None,
    cursor_id: Annotated[UUID | None, Query(alias="cursorId", description="커서 기준 파일 ID")] = None,
) -> FileItemListResponse:
    """파일 목록 조회 (MIME 타입 필터 지원)"""

    page = list_files(
        limit=limit,
        mime_type=mime_type,
        cursor_uploaded_at=cursor_uploaded_at,
        cursor_id=cursor_id,
    )

    return FileItemListResponse(
        items=[FileItem.model_validate(item) for item in page["items"]],
        has_more=page["has_more"],
        next_cursor_uploaded_at=page["next_cursor_uploaded_at"],
        next_cursor_id=page["next_cursor_id"],
    )
