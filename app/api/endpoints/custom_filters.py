import json
import logging

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
import io

from app.schemas.custom_filter import (
    CustomFilterCreate,
    CustomFilterListResponse,
    CustomFilterResponse,
    CustomFilterUpdate,
)
from app.services.custom_filters_service import (
    create_custom_filter,
    get_custom_filter,
    list_custom_filters,
    modify_custom_filter,
    remove_custom_filter,
    test_custom_filter,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get(
    "/custom-filters",
    tags=["custom-filter"],
    response_model=CustomFilterListResponse,
)
async def get_custom_filters() -> CustomFilterListResponse:
    """커스텀 필터 목록 조회"""
    items = list_custom_filters()
    return CustomFilterListResponse(
        items=[CustomFilterResponse.model_validate(item) for item in items],
    )


@router.get(
    "/custom-filters/{filter_id}",
    tags=["custom-filter"],
    response_model=CustomFilterResponse,
)
async def get_custom_filter_detail(filter_id: str) -> CustomFilterResponse:
    """커스텀 필터 상세 조회"""
    result = get_custom_filter(filter_id)
    if result is None:
        raise HTTPException(status_code=404, detail="custom filter not found")
    return CustomFilterResponse.model_validate(result)


@router.post(
    "/custom-filters",
    tags=["custom-filter"],
    response_model=CustomFilterResponse,
    status_code=201,
)
async def create_custom_filter_endpoint(
    body: CustomFilterCreate,
) -> CustomFilterResponse:
    """커스텀 필터 생성"""
    result = create_custom_filter(
        nm=body.nm,
        description=body.description,
        code=body.code,
        params=[p.model_dump() for p in body.params],
    )
    return CustomFilterResponse.model_validate(result)


@router.put(
    "/custom-filters/{filter_id}",
    tags=["custom-filter"],
    response_model=CustomFilterResponse,
)
async def update_custom_filter_endpoint(
    filter_id: str,
    body: CustomFilterUpdate,
) -> CustomFilterResponse:
    """커스텀 필터 수정"""
    result = modify_custom_filter(
        filter_id,
        nm=body.nm,
        description=body.description,
        code=body.code,
        params=[p.model_dump() for p in body.params] if body.params is not None else None,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="custom filter not found")
    return CustomFilterResponse.model_validate(result)


@router.delete(
    "/custom-filters/{filter_id}",
    tags=["custom-filter"],
    status_code=204,
)
async def delete_custom_filter_endpoint(filter_id: str) -> None:
    """커스텀 필터 삭제"""
    if not remove_custom_filter(filter_id):
        raise HTTPException(status_code=404, detail="custom filter not found")


@router.post(
    "/custom-filters/{filter_id}/test",
    tags=["custom-filter"],
)
async def test_custom_filter_endpoint(
    filter_id: str,
    image: UploadFile = File(...),
    parameters: str = Form("{}"),
) -> StreamingResponse:
    """커스텀 필터 테스트 실행 (이미지 첨부)"""
    filter_data = get_custom_filter(filter_id)
    if filter_data is None:
        raise HTTPException(status_code=404, detail="custom filter not found")

    params = json.loads(parameters)
    image_bytes = await image.read()

    result_bytes = test_custom_filter(
        code=filter_data["code"],
        image_bytes=image_bytes,
        params=params,
    )

    return StreamingResponse(
        io.BytesIO(result_bytes),
        media_type="image/png",
    )
