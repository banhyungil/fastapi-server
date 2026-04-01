from typing import Any

from app.repos.processes_repo import (
    insert_process,
    get_process_list,
    get_process_by_id,
    update_process,
    delete_process,
)


def create_process(
    *,
    nm: str,
    file_id: int,
    steps: list[dict[str, Any]],
) -> dict[str, Any]:
    return insert_process(nm=nm, file_id=file_id, steps=steps)


def list_processes(*, file_id: int | None = None) -> list[dict[str, Any]]:
    return get_process_list(file_id=file_id)


def get_process(process_id: int) -> dict[str, Any] | None:
    return get_process_by_id(process_id)


def modify_process(
    process_id: int,
    *,
    nm: str | None = None,
    final_file_id: int | None = None,
    is_latest: bool | None = None,
    total_execution_ms: int | None = None,
    steps: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    return update_process(
        process_id,
        nm=nm,
        final_file_id=final_file_id,
        is_latest=is_latest,
        total_execution_ms=total_execution_ms,
        steps=steps,
    )


def remove_process(process_id: int) -> bool:
    return delete_process(process_id)
