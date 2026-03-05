from datetime import datetime
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from app.core.config import settings


def _ensure_db() -> None:
    if not settings.database_url:
        raise RuntimeError("database_url is not configured")


def insert_preset(
    *,
    nm: str,
    description: str | None,
    is_system: bool,
    steps: list[dict[str, Any]],
) -> dict[str, Any]:
    _ensure_db()
    with psycopg.connect(settings.database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO t_preset (nm, description, is_system)
                VALUES (%s, %s, %s)
                RETURNING id::text, nm, description, is_system, created_at, updated_at
                """,
                (nm, description, is_system),
            )
            row = cur.fetchone()
            if row is None:
                raise RuntimeError("failed to insert preset")

            preset_id = row[0]
            inserted_steps = _insert_steps(cur, preset_id, steps)
        conn.commit()

    return {
        "id": row[0],
        "nm": row[1],
        "description": row[2],
        "is_system": row[3],
        "created_at": row[4],
        "updated_at": row[5],
        "steps": inserted_steps,
    }


def _insert_steps(
    cur: psycopg.Cursor[Any],
    preset_id: str,
    steps: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for step in steps:
        cur.execute(
            """
            INSERT INTO t_preset_step (preset_id, step_order, algorithm_nm, parameters, is_enabled)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id::text, step_order, algorithm_nm, parameters, is_enabled
            """,
            (preset_id, step["step_order"], step["algorithm_nm"], Jsonb(step.get("parameters", {})), step.get("is_enabled", True)),
        )
        r = cur.fetchone()
        if r:
            result.append({
                "id": r[0],
                "step_order": r[1],
                "algorithm_nm": r[2],
                "parameters": r[3],
                "is_enabled": r[4],
            })
    return result


def get_preset_list() -> list[dict[str, Any]]:
    _ensure_db()
    with psycopg.connect(settings.database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id::text, nm, description, is_system, created_at, updated_at
                FROM t_preset
                ORDER BY created_at DESC
                """
            )
            presets = cur.fetchall()

            result: list[dict[str, Any]] = []
            for p in presets:
                cur.execute(
                    """
                    SELECT id::text, step_order, algorithm_nm, parameters, is_enabled
                    FROM t_preset_step
                    WHERE preset_id = %s::uuid
                    ORDER BY step_order
                    """,
                    (p[0],),
                )
                steps = [
                    {
                        "id": s[0],
                        "step_order": s[1],
                        "algorithm_nm": s[2],
                        "parameters": s[3],
                        "is_enabled": s[4],
                    }
                    for s in cur.fetchall()
                ]
                result.append({
                    "id": p[0],
                    "nm": p[1],
                    "description": p[2],
                    "is_system": p[3],
                    "created_at": p[4],
                    "updated_at": p[5],
                    "steps": steps,
                })
    return result


def get_preset_by_id(preset_id: str) -> dict[str, Any] | None:
    _ensure_db()
    with psycopg.connect(settings.database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id::text, nm, description, is_system, created_at, updated_at
                FROM t_preset
                WHERE id = %s::uuid
                """,
                (preset_id,),
            )
            row = cur.fetchone()
            if row is None:
                return None

            cur.execute(
                """
                SELECT id::text, step_order, algorithm_nm, parameters, is_enabled
                FROM t_preset_step
                WHERE preset_id = %s::uuid
                ORDER BY step_order
                """,
                (preset_id,),
            )
            steps = [
                {
                    "id": s[0],
                    "step_order": s[1],
                    "algorithm_nm": s[2],
                    "parameters": s[3],
                    "is_enabled": s[4],
                }
                for s in cur.fetchall()
            ]

    return {
        "id": row[0],
        "nm": row[1],
        "description": row[2],
        "is_system": row[3],
        "created_at": row[4],
        "updated_at": row[5],
        "steps": steps,
    }


def update_preset(
    preset_id: str,
    *,
    nm: str | None = None,
    description: str | None = None,
    steps: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    _ensure_db()
    with psycopg.connect(settings.database_url) as conn:
        with conn.cursor() as cur:
            # 존재 확인
            cur.execute("SELECT id FROM t_preset WHERE id = %s::uuid", (preset_id,))
            if cur.fetchone() is None:
                return None

            # 마스터 업데이트
            updates: list[str] = ["updated_at = now()"]
            params: list[Any] = []
            if nm is not None:
                updates.append("nm = %s")
                params.append(nm)
            if description is not None:
                updates.append("description = %s")
                params.append(description)

            params.append(preset_id)
            cur.execute(
                f"UPDATE t_preset SET {', '.join(updates)} WHERE id = %s::uuid",
                params,
            )

            # steps 전체 교체
            if steps is not None:
                cur.execute("DELETE FROM t_preset_step WHERE preset_id = %s::uuid", (preset_id,))
                _insert_steps(cur, preset_id, steps)

        conn.commit()

    return get_preset_by_id(preset_id)


def delete_preset(preset_id: str) -> bool:
    _ensure_db()
    with psycopg.connect(settings.database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM t_preset WHERE id = %s::uuid RETURNING id",
                (preset_id,),
            )
            deleted = cur.fetchone() is not None
        conn.commit()
    return deleted
