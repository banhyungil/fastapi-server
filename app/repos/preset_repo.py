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
    """트리 구조 노드 삽입. client_id/parent_client_id 기반으로 부모를 매핑한다."""
    result: list[dict[str, Any]] = []
    # client_id → 실제 DB step id 매핑
    client_to_db: dict[str, str] = {}

    for step in steps:
        parent_client_id = step.get("parent_client_id")
        db_parent_id = client_to_db.get(parent_client_id) if parent_client_id else None

        cur.execute(
            """
            INSERT INTO t_preset_step (preset_id, parent_id, step_order, algorithm_nm, parameters)
            VALUES (%s::uuid, %s::uuid, %s, %s, %s)
            RETURNING id::text, parent_id::text, step_order, algorithm_nm, parameters
            """,
            (
                preset_id,
                db_parent_id,
                step.get("step_order", 0),
                step["algorithm_nm"],
                Jsonb(step.get("parameters", {})),
            ),
        )
        r = cur.fetchone()
        if r:
            db_id = r[0]
            client_id = step.get("client_id")
            if client_id:
                client_to_db[client_id] = db_id
            result.append({
                "id": db_id,
                "parent_id": r[1],
                "step_order": r[2],
                "algorithm_nm": r[3],
                "parameters": r[4],
            })
    return result


def _fetch_steps(cur: psycopg.Cursor[Any], preset_id: str) -> list[dict[str, Any]]:
    cur.execute(
        """
        SELECT id::text, parent_id::text, step_order, algorithm_nm, parameters
        FROM t_preset_step
        WHERE preset_id = %s::uuid
        ORDER BY step_order
        """,
        (preset_id,),
    )
    return [
        {
            "id": s[0],
            "parent_id": s[1],
            "step_order": s[2],
            "algorithm_nm": s[3],
            "parameters": s[4],
        }
        for s in cur.fetchall()
    ]


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
                steps = _fetch_steps(cur, p[0])
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

            steps = _fetch_steps(cur, preset_id)

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
            cur.execute("SELECT id FROM t_preset WHERE id = %s::uuid", (preset_id,))
            if cur.fetchone() is None:
                return None

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
