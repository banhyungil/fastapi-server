from datetime import datetime
from typing import Unpack
from uuid import UUID

from app.repos.file_repo import FileRowInput, FileRowPage, InsertedFileMeta, insert_file_row, get_file_list


def insert_file(**kwargs: Unpack[FileRowInput]) -> InsertedFileMeta:
    return insert_file_row(**kwargs)


def list_files(
    *,
    limit: int,
    cursor_uploaded_at: datetime | None = None,
    cursor_id: UUID | None = None,
) -> FileRowPage:
    return get_file_list(
        limit=limit,
        cursor_uploaded_at=cursor_uploaded_at,
        cursor_id=cursor_id,
    )