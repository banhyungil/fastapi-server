"""필터 메타데이터(파라미터 스키마) 조회 엔드포인트."""

from typing import Any

from fastapi import APIRouter, HTTPException

from app.schemas.file import FilterType
from app.schemas.image_processing import PARAM_MODELS

router = APIRouter()


@router.get("/filters/params/{filter_type}", tags=["filters"])
async def get_filter_params(filter_type: FilterType) -> dict[str, Any]:
    """필터별 파라미터 스키마 조회."""
    param_cls = PARAM_MODELS.get(filter_type)
    if param_cls is None:
        raise HTTPException(status_code=400, detail=f"unsupported filterType: {filter_type}")
    schema = param_cls.model_json_schema(by_alias=True)
    return {"filterType": filter_type, "schema": schema}


@router.get("/filters/params", tags=["filters"])
async def get_all_filter_params() -> dict[str, Any]:
    """전체 필터 파라미터 스키마 목록 조회."""
    return {
        filter_type: PARAM_MODELS[filter_type].model_json_schema(by_alias=True)
        for filter_type in PARAM_MODELS
    }
