from typing import Any

import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb

from app.core.config import settings
from app.core.database import pool


def _ensure_db() -> None:
    if not settings.database_url:
        raise RuntimeError("database_url is not configured")


def insert_process(
    *,
    nm: str,
    file_id: int,
    steps: list[dict[str, Any]],
) -> dict[str, Any]:
    _ensure_db()
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO t_image_process (nm, file_id)
                VALUES (%s, %s)
                RETURNING id, nm, file_id,
                          (SELECT path FROM t_file WHERE id = file_id) AS file_path,
                          final_file_id,
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
    process_id: int,
    steps: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """트리 구조 노드 삽입. client_id/parent_client_id 기반으로 부모를 매핑한다."""
    result: list[dict[str, Any]] = []
    client_to_db: dict[str, str] = {}

    for step in steps:
        parent_client_id = step.get("parent_client_id")
        db_parent_id = client_to_db.get(parent_client_id) if parent_client_id else None

        cur.execute(
            """
            INSERT INTO t_process_step
                (process_id, parent_id, preset_id, step_order, algorithm_nm, parameters, is_enabled)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id, process_id, parent_id, preset_id, step_order,
                      algorithm_nm, parameters, is_enabled, created_at, execution_ms
            """,
            (
                process_id,
                db_parent_id,
                step.get("preset_id"),
                step["step_order"],
                step["algorithm_nm"],
                Jsonb(step.get("parameters", {})),
                step.get("is_enabled", True),
            ),
        )
        r = cur.fetchone()
        if r:
            db_id = r[0]
            client_id = step.get("client_id")
            if client_id:
                client_to_db[client_id] = db_id
            result.append(_step_row_to_dict(r))
    return result


def _step_row_to_dict(r: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "id": r[0],
        "process_id": r[1],
        "parent_id": r[2],
        "preset_id": r[3],
        "step_order": r[4],
        "algorithm_nm": r[5],
        "parameters": r[6],
        "is_enabled": r[7],
        "created_at": r[8],
        "execution_ms": r[9],
    }


def _row_to_dict(row: tuple[Any, ...], steps: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "id": row[0],
        "nm": row[1],
        "file_id": row[2],
        "file_path": row[3],
        "final_file_id": row[4],
        "is_latest": row[5],
        "total_execution_ms": row[6],
        "created_at": row[7],
        "updated_at": row[8],
        "steps": steps,
    }


def _fetch_steps(cur: psycopg.Cursor[Any], process_id: int) -> list[dict[str, Any]]:
    cur.execute(
        """
        SELECT id, process_id, parent_id, preset_id, step_order,
               algorithm_nm, parameters, is_enabled, created_at, execution_ms
        FROM t_process_step
        WHERE process_id = %s
        ORDER BY step_order
        """,
        (process_id,),
    )
    return [_step_row_to_dict(s) for s in cur.fetchall()]


def get_process_list(*, file_id: int | None = None) -> list[dict[str, Any]]:
    _ensure_db()
    with pool.connection() as conn:
        with conn.cursor() as cur:
            query = """
                SELECT p.id, p.nm, p.file_id, f.path AS file_path,
                       p.final_file_id,
                       p.is_latest, p.total_execution_ms, p.created_at, p.updated_at
                FROM t_image_process p
                LEFT JOIN t_file f ON f.id = p.file_id
            """
            params: list[Any] = []
            if file_id is not None:
                query += " WHERE p.file_id = %s"
                params.append(file_id)
            query += " ORDER BY p.created_at DESC"

            cur.execute(query, params)
            processes = cur.fetchall()

            result: list[dict[str, Any]] = []
            for p in processes:
                steps = _fetch_steps(cur, p[0])
                result.append(_row_to_dict(p, steps))
    return result


def get_process_by_id(process_id: int) -> dict[str, Any] | None:
    _ensure_db()
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT p.id, p.nm, p.file_id, f.path AS file_path,
                       p.final_file_id,
                       p.is_latest, p.total_execution_ms, p.created_at, p.updated_at
                FROM t_image_process p
                LEFT JOIN t_file f ON f.id = p.file_id
                WHERE p.id = %s
                """,
                (process_id,),
            )
            row = cur.fetchone()
            if row is None:
                return None

            steps = _fetch_steps(cur, process_id)

    return _row_to_dict(row, steps)


def update_process(
    process_id: int,
    *,
    nm: str | None = None,
    final_file_id: int | None = None,
    is_latest: bool | None = None,
    total_execution_ms: int | None = None,
    steps: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    _ensure_db()
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM t_image_process WHERE id = %s", (process_id,))
            if cur.fetchone() is None:
                return None

            updates: list[sql.SQL] = [sql.SQL("updated_at = now()")]
            params: list[Any] = []
            if nm is not None:
                updates.append(sql.SQL("nm = %s"))
                params.append(nm)
            if final_file_id is not None:
                updates.append(sql.SQL("final_file_id = %s"))
                params.append(final_file_id)
            if is_latest is not None:
                updates.append(sql.SQL("is_latest = %s"))
                params.append(is_latest)
            if total_execution_ms is not None:
                updates.append(sql.SQL("total_execution_ms = %s"))
                params.append(total_execution_ms)

            params.append(process_id)
            query = sql.SQL("UPDATE t_image_process SET {} WHERE id = %s").format(
                sql.SQL(", ").join(updates),
            )
            cur.execute(query, params)

            if steps is not None:
                cur.execute("DELETE FROM t_process_step WHERE process_id = %s", (process_id,))
                _insert_steps(cur, process_id, steps)

        conn.commit()

    return get_process_by_id(process_id)


def delete_process(process_id: int) -> bool:
    _ensure_db()
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM t_image_process WHERE id = %s RETURNING id",
                (process_id,),
            )
            deleted = cur.fetchone() is not None
        conn.commit()
    return deleted
