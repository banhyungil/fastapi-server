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
    content_hash: NotRequired[str | None]
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


def find_by_content_hash(content_hash: str) -> FileRow | None:
    """동일 content_hash를 가진 기존 파일이 있으면 반환"""
    if not settings.database_url:
        raise RuntimeError("database_url is not configured")

    with psycopg.connect(settings.database_url) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id::text, origin_nm, nm, path, mime_type, size_bytes, uploaded_at, options
                FROM t_file WHERE content_hash = %s LIMIT 1
                """,
                (content_hash,),
            )
            row = cursor.fetchone()

    if row is None:
        return None
    return {
        "id": str(row[0]),
        "origin_nm": row[1],
        "nm": row[2],
        "path": row[3],
        "mime_type": row[4],
        "size_bytes": row[5],
        "uploaded_at": row[6],
        "options": row[7],
    }


# Unpack을 이용해 키워드 파라미터에 타입 바인딩 가능
def insert_file_row(**kwargs: Unpack[FileRowInput]) -> InsertedFileMeta:
    """T_FILE 데이터 저장"""
    if not settings.database_url:
        raise RuntimeError("database_url is not configured")

    with psycopg.connect(settings.database_url) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO t_file (origin_nm, nm, path, mime_type, size_bytes, uploader_id, options, content_hash)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, uploaded_at
                """,
                (
                    kwargs["origin_nm"], kwargs["nm"], kwargs["path"],
                    kwargs["mime_type"], kwargs["size_bytes"],
                    kwargs.get("uploader_id"), Jsonb(kwargs["options"]),
                    kwargs.get("content_hash"),
                ),
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
    mime_type: str | None = None,
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
    conditions: list[str] = []

    if mime_type is not None:
        if mime_type.endswith("/*"):
            # 와일드카드: "image/*" → mime_type LIKE 'image/%'
            conditions.append("mime_type LIKE %s")
            params.append(mime_type.replace("/*", "/%"))
        else:
            conditions.append("mime_type = %s")
            params.append(mime_type)

    if cursor_uploaded_at is not None and cursor_id is not None:
        conditions.append("(uploaded_at, id) < (%s, %s)")
        params.extend([cursor_uploaded_at, cursor_id])

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

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