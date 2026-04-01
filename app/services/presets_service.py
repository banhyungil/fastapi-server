from typing import Any

from app.repos.presets_repo import (
    insert_preset,
    get_preset_list,
    get_preset_by_id,
    update_preset,
    delete_preset,
)


def create_preset(
    *,
    nm: str,
    description: str | None,
    is_system: bool,
    steps: list[dict[str, Any]],
) -> dict[str, Any]:
    return insert_preset(nm=nm, description=description, is_system=is_system, steps=steps)


def list_presets() -> list[dict[str, Any]]:
    return get_preset_list()


def get_preset(preset_id: int) -> dict[str, Any] | None:
    return get_preset_by_id(preset_id)


def modify_preset(
    preset_id: int,
    *,
    nm: str | None = None,
    description: str | None = None,
    steps: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    return update_preset(preset_id, nm=nm, description=description, steps=steps)


def remove_preset(preset_id: int) -> bool:
    return delete_preset(preset_id)
