from datetime import datetime
from typing import Unpack
from uuid import UUID

from pathlib import Path

from app.repos.file_repo import FileRow, FileRowInput, FileRowPage, InsertedFileMeta, insert_file_row, get_file_list, find_by_content_hash, find_by_id, delete_by_id, update_origin_nm
from app.services.image_processing_service import delete_file_thumbnail


def insert_file(**kwargs: Unpack[FileRowInput]) -> InsertedFileMeta:
    return insert_file_row(**kwargs)


def find_file_by_id(file_id: str) -> FileRow | None:
    return find_by_id(file_id)


def find_file_by_hash(content_hash: str) -> FileRow | None:
    return find_by_content_hash(content_hash)


def list_files(
    *,
    limit: int,
    mime_type: str | None = None,
    search: str | None = None,
    min_size: int | None = None,
    max_size: int | None = None,
    cursor_uploaded_at: datetime | None = None,
    cursor_id: UUID | None = None,
) -> FileRowPage:
    return get_file_list(
        limit=limit,
        mime_type=mime_type,
        search=search,
        min_size=min_size,
        max_size=max_size,
        cursor_uploaded_at=cursor_uploaded_at,
        cursor_id=cursor_id,
    )


def delete_file(file_id: str) -> FileRow:
    """파일 메타데이터 삭제 + 디스크 파일 삭제"""
    deleted = delete_by_id(file_id)
    if deleted is None:
        raise ValueError(f"file not found: {file_id}")

    disk_path = Path(deleted["path"])
    if disk_path.exists():
        disk_path.unlink()

    delete_file_thumbnail(str(deleted["id"]))

    return deleted


def rename_file(file_id: str, origin_nm: str) -> FileRow:
    """파일명(origin_nm) 수정"""
    updated = update_origin_nm(file_id, origin_nm)
    if updated is None:
        raise ValueError(f"file not found: {file_id}")
    return updated