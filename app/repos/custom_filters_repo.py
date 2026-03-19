from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from app.core.config import settings


def _ensure_db() -> None:
    if not settings.database_url:
        raise RuntimeError("database_url is not configured")


def insert_custom_filter(
    *,
    nm: str,
    description: str,
    code: str,
    params: list[dict[str, Any]],
) -> dict[str, Any]:
    _ensure_db()
    with psycopg.connect(settings.database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO t_custom_filter (nm, description, code, params)
                VALUES (%s, %s, %s, %s)
                RETURNING id::text, nm, description, code, params,
                          version, created_at, updated_at
                """,
                (nm, description, code, Jsonb(params)),
            )
            row = cur.fetchone()
            if row is None:
                raise RuntimeError("failed to insert custom filter")
        conn.commit()

    return _row_to_dict(row)


def get_custom_filter_list() -> list[dict[str, Any]]:
    _ensure_db()
    with psycopg.connect(settings.database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id::text, nm, description, code, params,
                       version, created_at, updated_at
                FROM t_custom_filter
                ORDER BY created_at DESC
                """
            )
            return [_row_to_dict(row) for row in cur.fetchall()]


def get_custom_filter_by_id(filter_id: str) -> dict[str, Any] | None:
    _ensure_db()
    with psycopg.connect(settings.database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id::text, nm, description, code, params,
                       version, created_at, updated_at
                FROM t_custom_filter
                WHERE id = %s::uuid
                """,
                (filter_id,),
            )
            row = cur.fetchone()
            return _row_to_dict(row) if row else None


def update_custom_filter(
    filter_id: str,
    *,
    nm: str | None = None,
    description: str | None = None,
    code: str | None = None,
    params: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    _ensure_db()
    with psycopg.connect(settings.database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM t_custom_filter WHERE id = %s::uuid",
                (filter_id,),
            )
            if cur.fetchone() is None:
                return None

            sets: list[str] = ["updated_at = now()"]
            values: list[Any] = []

            if nm is not None:
                sets.append("nm = %s")
                values.append(nm)
            if description is not None:
                sets.append("description = %s")
                values.append(description)
            if code is not None:
                sets.append("code = %s")
                sets.append("version = version + 1")
                values.append(code)
            if params is not None:
                sets.append("params = %s")
                values.append(Jsonb(params))

            values.append(filter_id)
            cur.execute(
                f"UPDATE t_custom_filter SET {', '.join(sets)} WHERE id = %s::uuid",
                values,
            )
        conn.commit()

    return get_custom_filter_by_id(filter_id)


def delete_custom_filter(filter_id: str) -> bool:
    _ensure_db()
    with psycopg.connect(settings.database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM t_custom_filter WHERE id = %s::uuid RETURNING id",
                (filter_id,),
            )
            deleted = cur.fetchone() is not None
        conn.commit()
    return deleted


def _row_to_dict(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "id": row[0],
        "nm": row[1],
        "description": row[2],
        "code": row[3],
        "params": row[4],
        "version": row[5],
        "created_at": row[6],
        "updated_at": row[7],
    }
