from datetime import datetime
from typing import TypedDict, NotRequired, Any, Unpack
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb

from app.core.config import settings

class FileRowInput(TypedDict):
    origin_nm: str
    nm: str
    path: str
    mime_type: str
    size_bytes: int
    options: dict[str, Any]
    uploader_id: NotRequired[UUID | None]


class InsertedFileMeta(TypedDict):
    id: str
    uploaded_at: datetime


class FileRow(TypedDict):
    id: str
    origin_nm: str
    nm: str
    path: str
    mime_type: str
    size_bytes: int
    uploaded_at: datetime
    options: dict[str, Any]


class FileRowPage(TypedDict):
    items: list[FileRow]
    has_more: bool
    next_cursor_uploaded_at: datetime | None
    next_cursor_id: str | None


# Unpack을 이용해 키워드 파라미터에 타입 바인딩 가능
def insert_file_row(**kwargs: Unpack[FileRowInput]) -> InsertedFileMeta:
    if not settings.database_url:
        raise RuntimeError("database_url is not configured")
    """T_FILE 데이터 저장
    """
    

    # with: context manager
    # 기본 형태: with 객체 as 변수:
    # 내부적으로는 객체의 __enter__() / __exit__()를 호출
    # 사실상 try/finally를 간결하게 쓴 문법
    # 블록 안에서 예외가 나도 __exit__()가 호출되어 정리(닫기) 수행
    with psycopg.connect(settings.database_url) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO t_file (origin_nm, nm, path, mime_type, size_bytes, uploader_id, options)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id, uploaded_at
                """,
                (kwargs["origin_nm"], kwargs["nm"], kwargs["path"], kwargs["mime_type"], kwargs["size_bytes"], kwargs.get("uploader_id"), Jsonb(kwargs["options"])),
            )
            row = cursor.fetchone()

        conn.commit()

    if row is None:
        raise RuntimeError("failed to insert file metadata")

    return {
        "id": str(row[0]),
        "uploaded_at": row[1],
    }


def get_file_list(
    *,
    limit: int,
    cursor_uploaded_at: datetime | None = None,
    cursor_id: UUID | None = None,
) -> FileRowPage:
    if not settings.database_url:
        raise RuntimeError("database_url is not configured")

    query = """
        SELECT id::text, origin_nm, nm, path, mime_type, size_bytes, uploaded_at, options
        FROM t_file
    """
    params: list[object] = []

    if cursor_uploaded_at is not None and cursor_id is not None:
        query += """
            WHERE (uploaded_at, id) < (%s, %s)
        """
        params.extend([cursor_uploaded_at, cursor_id])

    query += """
        ORDER BY uploaded_at DESC, id DESC
        LIMIT %s
    """
    params.append(limit + 1)

    with psycopg.connect(settings.database_url) as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()

    has_more = len(rows) > limit
    visible_rows = rows[:limit]

    items: list[FileRow] = [
        {
            "id": str(row[0]),
            "origin_nm": row[1],
            "nm": row[2],
            "path": row[3],
            "mime_type": row[4],
            "size_bytes": row[5],
            "uploaded_at": row[6],
            "options": row[7],
        }
        for row in visible_rows
    ]

    if not items or not has_more:
        return {
            "items": items,
            "has_more": has_more,
            "next_cursor_uploaded_at": None,
            "next_cursor_id": None,
        }

    last_item = items[-1]
    return {
        "items": items,
        "has_more": has_more,
        "next_cursor_uploaded_at": last_item["uploaded_at"],
        "next_cursor_id": last_item["id"],
    }