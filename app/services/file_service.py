from datetime import datetime
from uuid import UUID
from typing import Any

from app.repos.file_repo import FileRowPage, InsertedFileMeta, insert_file_row, list_file_rows


def insert_file(
    *,
    origin_nm: str,
    nm: str,
    path: str,
    mime_type: str,
    size_bytes: int,
    uploader_id: UUID | None = None,
    options: dict[str, Any]
) -> InsertedFileMeta:
    return insert_file_row(
        origin_nm=origin_nm,
        nm=nm,
        path=path,
        mime_type=mime_type,
        size_bytes=size_bytes,
        uploader_id=uploader_id,
        options=options
    )


def list_files(
    *,
    limit: int,
    cursor_uploaded_at: datetime | None = None,
    cursor_id: UUID | None = None,
) -> FileRowPage:
    return list_file_rows(
        limit=limit,
        cursor_uploaded_at=cursor_uploaded_at,
        cursor_id=cursor_id,
    )