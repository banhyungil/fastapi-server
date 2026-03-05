from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from app.core.config import settings


def _ensure_db() -> None:
    if not settings.database_url:
        raise RuntimeError("database_url is not configured")


def insert_process(
    *,
    nm: str,
    file_id: str,
    steps: list[dict[str, Any]],
) -> dict[str, Any]:
    _ensure_db()
    with psycopg.connect(settings.database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO t_image_process (nm, file_id)
                VALUES (%s, %s::uuid)
                RETURNING id::text, nm, file_id::text, final_file_id::text,
                          is_latest, total_execution_ms, created_at, updated_at
                """,
                (nm, file_id),
            )
            row = cur.fetchone()
            if row is None:
                raise RuntimeError("failed to insert process")

            process_id = row[0]
            inserted_steps = _insert_steps(cur, process_id, steps)
        conn.commit()

    return _row_to_dict(row, inserted_steps)


def _insert_steps(
    cur: psycopg.Cursor[Any],
    process_id: str,
    steps: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for step in steps:
        cur.execute(
            """
            INSERT INTO t_process_step (process_id, preset_id, step_order, algorithm_nm, parameters, is_enabled)
            VALUES (%s::uuid, %s, %s, %s, %s, %s)
            RETURNING id::text, process_id::text, preset_id::text, step_order,
                      algorithm_nm, parameters, is_enabled, created_at, execution_ms
            """,
            (
                process_id,
                step.get("preset_id"),
                step["step_order"],
                step["algorithm_nm"],
                Jsonb(step.get("parameters", {})),
                step.get("is_enabled", True),
            ),
        )
        r = cur.fetchone()
        if r:
            result.append(_step_row_to_dict(r))
    return result


def _step_row_to_dict(r: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "id": r[0],
        "process_id": r[1],
        "preset_id": r[2],
        "step_order": r[3],
        "algorithm_nm": r[4],
        "parameters": r[5],
        "is_enabled": r[6],
        "created_at": r[7],
        "execution_ms": r[8],
    }


def _row_to_dict(row: tuple[Any, ...], steps: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "id": row[0],
        "nm": row[1],
        "file_id": row[2],
        "final_file_id": row[3],
        "is_latest": row[4],
        "total_execution_ms": row[5],
        "created_at": row[6],
        "updated_at": row[7],
        "steps": steps,
    }


def get_process_list(*, file_id: str | None = None) -> list[dict[str, Any]]:
    _ensure_db()
    with psycopg.connect(settings.database_url) as conn:
        with conn.cursor() as cur:
            query = """
                SELECT id::text, nm, file_id::text, final_file_id::text,
                       is_latest, total_execution_ms, created_at, updated_at
                FROM t_image_process
            """
            params: list[Any] = []
            if file_id is not None:
                query += " WHERE file_id = %s::uuid"
                params.append(file_id)
            query += " ORDER BY created_at DESC"

            cur.execute(query, params)
            processes = cur.fetchall()

            result: list[dict[str, Any]] = []
            for p in processes:
                cur.execute(
                    """
                    SELECT id::text, process_id::text, preset_id::text, step_order,
                           algorithm_nm, parameters, is_enabled, created_at, execution_ms
                    FROM t_process_step
                    WHERE process_id = %s::uuid
                    ORDER BY step_order
                    """,
                    (p[0],),
                )
                steps = [_step_row_to_dict(s) for s in cur.fetchall()]
                result.append(_row_to_dict(p, steps))
    return result


def get_process_by_id(process_id: str) -> dict[str, Any] | None:
    _ensure_db()
    with psycopg.connect(settings.database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id::text, nm, file_id::text, final_file_id::text,
                       is_latest, total_execution_ms, created_at, updated_at
                FROM t_image_process
                WHERE id = %s::uuid
                """,
                (process_id,),
            )
            row = cur.fetchone()
            if row is None:
                return None

            cur.execute(
                """
                SELECT id::text, process_id::text, preset_id::text, step_order,
                       algorithm_nm, parameters, is_enabled, created_at, execution_ms
                FROM t_process_step
                WHERE process_id = %s::uuid
                ORDER BY step_order
                """,
                (process_id,),
            )
            steps = [_step_row_to_dict(s) for s in cur.fetchall()]

    return _row_to_dict(row, steps)


def update_process(
    process_id: str,
    *,
    nm: str | None = None,
    final_file_id: str | None = None,
    is_latest: bool | None = None,
    total_execution_ms: int | None = None,
    steps: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    _ensure_db()
    with psycopg.connect(settings.database_url) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM t_image_process WHERE id = %s::uuid", (process_id,))
            if cur.fetchone() is None:
                return None

            updates: list[str] = ["updated_at = now()"]
            params: list[Any] = []
            if nm is not None:
                updates.append("nm = %s")
                params.append(nm)
            if final_file_id is not None:
                updates.append("final_file_id = %s::uuid")
                params.append(final_file_id)
            if is_latest is not None:
                updates.append("is_latest = %s")
                params.append(is_latest)
            if total_execution_ms is not None:
                updates.append("total_execution_ms = %s")
                params.append(total_execution_ms)

            params.append(process_id)
            cur.execute(
                f"UPDATE t_image_process SET {', '.join(updates)} WHERE id = %s::uuid",
                params,
            )

            if steps is not None:
                cur.execute("DELETE FROM t_process_step WHERE process_id = %s::uuid", (process_id,))
                _insert_steps(cur, process_id, steps)

        conn.commit()

    return get_process_by_id(process_id)


def delete_process(process_id: str) -> bool:
    _ensure_db()
    with psycopg.connect(settings.database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM t_image_process WHERE id = %s::uuid RETURNING id",
                (process_id,),
            )
            deleted = cur.fetchone() is not None
        conn.commit()
    return deleted
