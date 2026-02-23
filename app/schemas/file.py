from datetime import datetime

from pydantic import BaseModel, ConfigDict


def to_camel(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class FileSaveResponse(CamelModel):
    id: str
    origin_nm: str
    nm: str
    path: str
    mime_type: str
    size_bytes: int
    uploaded_at: datetime


class FileListItem(CamelModel):
    id: str
    origin_nm: str
    nm: str
    path: str
    mime_type: str
    size_bytes: int
    uploaded_at: datetime


class FileListResponse(CamelModel):
    items: list[FileListItem]
    has_more: bool
    next_cursor_uploaded_at: datetime | None = None
    next_cursor_id: str | None = None