import logging
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app.schemas.process import (
    ProcessCreate,
    ProcessUpdate,
    ProcessResponse,
    ProcessListResponse,
)
from app.services.process_service import (
    create_process,
    list_processes,
    get_process,
    modify_process,
    remove_process,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/processes", tags=["process"], response_model=ProcessListResponse)
async def get_processes(
    file_id: Annotated[str | None, Query(alias="fileId", description="원본 파일 ID로 필터")] = None,
) -> ProcessListResponse:
    """처리연산 목록 조회"""
    items = list_processes(file_id=file_id)
    return ProcessListResponse(
        items=[ProcessResponse.model_validate(item) for item in items],
    )


@router.get("/processes/{process_id}", tags=["process"], response_model=ProcessResponse)
async def get_process_detail(process_id: str) -> ProcessResponse:
    """처리연산 상세 조회"""
    result = get_process(process_id)
    if result is None:
        raise HTTPException(status_code=404, detail="process not found")
    return ProcessResponse.model_validate(result)


@router.post("/processes", tags=["process"], response_model=ProcessResponse, status_code=201)
async def create_process_endpoint(body: ProcessCreate) -> ProcessResponse:
    """처리연산 생성"""
    steps = [step.model_dump() for step in body.steps]
    result = create_process(
        nm=body.nm,
        file_id=body.file_id,
        steps=steps,
    )
    return ProcessResponse.model_validate(result)


@router.put("/processes/{process_id}", tags=["process"], response_model=ProcessResponse)
async def update_process_endpoint(process_id: str, body: ProcessUpdate) -> ProcessResponse:
    """처리연산 수정"""
    steps = [step.model_dump() for step in body.steps] if body.steps is not None else None
    result = modify_process(
        process_id,
        nm=body.nm,
        final_file_id=body.final_file_id,
        is_latest=body.is_latest,
        total_execution_ms=body.total_execution_ms,
        steps=steps,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="process not found")
    return ProcessResponse.model_validate(result)


@router.delete("/processes/{process_id}", tags=["process"], status_code=204)
async def delete_process_endpoint(process_id: str) -> None:
    """처리연산 삭제"""
    if not remove_process(process_id):
        raise HTTPException(status_code=404, detail="process not found")
