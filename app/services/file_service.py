from datetime import datetime
from typing import Unpack
from uuid import UUID

from app.repos.file_repo import FileRow, FileRowInput, FileRowPage, InsertedFileMeta, insert_file_row, get_file_list, find_by_content_hash, find_by_id


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
    cursor_uploaded_at: datetime | None = None,
    cursor_id: UUID | None = None,
) -> FileRowPage:
    return get_file_list(
        limit=limit,
        mime_type=mime_type,
        cursor_uploaded_at=cursor_uploaded_at,
        cursor_id=cursor_id,
    )