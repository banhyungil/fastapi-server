"""필터 메타데이터(파라미터 스키마) 조회 엔드포인트."""

from typing import Any

from fastapi import APIRouter, HTTPException

from app.schemas.file import PrcType
from app.schemas.image_processing import PARAM_MODELS

router = APIRouter()


@router.get("/filters/params/{prc_type}", tags=["filters"])
async def get_filter_params(prc_type: PrcType) -> dict[str, Any]:
    """필터별 파라미터 스키마 조회."""
    param_cls = PARAM_MODELS.get(prc_type)
    if param_cls is None:
        raise HTTPException(status_code=400, detail=f"unsupported prcType: {prc_type}")
    schema = param_cls.model_json_schema(by_alias=True)
    return {"prcType": prc_type, "schema": schema}


@router.get("/filters/params", tags=["filters"])
async def get_all_filter_params() -> dict[str, Any]:
    """전체 필터 파라미터 스키마 목록 조회."""
    return {
        prc_type: PARAM_MODELS[prc_type].model_json_schema(by_alias=True)
        for prc_type in PARAM_MODELS
    }
