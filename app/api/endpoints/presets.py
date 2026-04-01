import logging

from fastapi import APIRouter, HTTPException

from app.schemas.presets_schema import (
    PresetCreate,
    PresetUpdate,
    PresetResponse,
    PresetListResponse,
)
from app.services.presets_service import (
    create_preset,
    list_presets,
    get_preset,
    modify_preset,
    remove_preset,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/presets", tags=["preset"], response_model=PresetListResponse)
async def get_presets() -> PresetListResponse:
    """프리셋 목록 조회"""
    items = list_presets()
    return PresetListResponse(
        items=[PresetResponse.model_validate(item) for item in items],
    )


@router.get("/presets/{preset_id}", tags=["preset"], response_model=PresetResponse)
async def get_preset_detail(preset_id: int) -> PresetResponse:
    """프리셋 상세 조회"""
    result = get_preset(preset_id)
    if result is None:
        raise HTTPException(status_code=404, detail="preset not found")
    return PresetResponse.model_validate(result)


@router.post("/presets", tags=["preset"], response_model=PresetResponse, status_code=201)
async def create_preset_endpoint(body: PresetCreate) -> PresetResponse:
    """프리셋 생성"""
    steps = [step.model_dump() for step in body.steps]
    result = create_preset(
        nm=body.nm,
        description=body.description,
        is_system=body.is_system,
        steps=steps,
    )
    return PresetResponse.model_validate(result)


@router.put("/presets/{preset_id}", tags=["preset"], response_model=PresetResponse)
async def update_preset_endpoint(preset_id: int, body: PresetUpdate) -> PresetResponse:
    """프리셋 수정"""
    steps = [step.model_dump() for step in body.steps] if body.steps is not None else None
    result = modify_preset(
        preset_id,
        nm=body.nm,
        description=body.description,
        steps=steps,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="preset not found")
    return PresetResponse.model_validate(result)


@router.delete("/presets/{preset_id}", tags=["preset"], status_code=204)
async def delete_preset_endpoint(preset_id: int) -> None:
    """프리셋 삭제"""
    if not remove_preset(preset_id):
        raise HTTPException(status_code=404, detail="preset not found")
