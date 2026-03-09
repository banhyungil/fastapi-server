# 외부 패키지는 패키지명으로 import
from hashlib import sha256
from io import BytesIO
import json
import logging
from pathlib import Path
from typing import Annotated, Any
from uuid import uuid4
from uuid import UUID
from datetime import datetime
import time

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import ValidationError

# 절대 import
from app.schemas.file import TFile, FileListResponse, FileSaveResponse, FileSaveOptions, FileUploadResponse, PrcType, TreeBatchResponse, TreeNodeResultResponse
from app.services.file_service import insert_file, list_files, find_file_by_hash
from app.schemas.image_processing import PARAM_MODELS
from app.services.image_processing_service import process_image, process_image_batch, process_image_batch_tree

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/image-processing", tags=["img-processing"], response_model=FileListResponse)
async def get_saved_images(
    limit: Annotated[int, Query(ge=1, le=100, description="반환할 최대 항목 수")] = 20,
    cursor_uploaded_at: Annotated[datetime | None, Query(alias="cursorUploadedAt", description="커서 기준 업로드 시각 (cursorId와 함께 제공)")] = None,
    cursor_id: Annotated[UUID | None, Query(alias="cursorId", description="커서 기준 파일 ID (cursorUploadedAt와 함께 제공)")] = None,
) -> FileListResponse:
    """처리 이미지 조회"""

    if (cursor_uploaded_at is None) != (cursor_id is None):
        raise HTTPException(status_code=400, detail="cursorUploadedAt and cursorId must be provided together")

    page = list_files(
        limit=limit,
        cursor_uploaded_at=cursor_uploaded_at,
        cursor_id=cursor_id,
    )

    return FileListResponse(
        # model_validate 사용 시 중첩 dict구조도 변환한다
        items=[TFile.model_validate(item) for item in page["items"]],
        has_more=page["has_more"],
        next_cursor_uploaded_at=page["next_cursor_uploaded_at"],
        next_cursor_id=page["next_cursor_id"],
    )


@router.get("/image-processing/params/{prc_type}", tags=["img-processing"])
async def get_filter_params(
    prc_type: PrcType,
) -> dict[str, Any]:
    """필터별 파라미터 스키마 조회. parameters JSON 작성 시 참고."""
    param_cls = PARAM_MODELS.get(prc_type)
    if param_cls is None:
        raise HTTPException(status_code=400, detail=f"unsupported prcType: {prc_type}")
    schema = param_cls.model_json_schema(by_alias=True)
    return {"prcType": prc_type, "schema": schema}


@router.get("/image-processing/params", tags=["img-processing"])
async def get_all_filter_params() -> dict[str, Any]:
    """전체 필터 파라미터 스키마 목록 조회."""
    return {
        prc_type: PARAM_MODELS[prc_type].model_json_schema(by_alias=True)
        for prc_type in PARAM_MODELS
    }


@router.post("/image-processing", tags=["img-processing"])
async def img_processing(
    file: Annotated[UploadFile, File(description="처리할 원본 이미지 파일")],
    prc_type: Annotated[PrcType, Form(alias="prcType", description="적용할 이미지 처리 종류")],
    parameters: Annotated[str | None, Form(
        description="필터별 파라미터 JSON 문자열. GET /image-processing/params/{prcType}에서 스키마 확인 가능",
        json_schema_extra={"description": "필터별 파라미터 JSON 문자열. GET /image-processing/params/{prcType}에서 스키마 확인 가능"},
        openapi_examples={
            "bilateral": {"summary": "bilateralFilter", "value": '{"d": 9, "sigmaColor": 100, "sigmaSpace": 50}'},
            "canny": {"summary": "canny", "value": '{"threshold1": 50, "threshold2": 150, "apertureSize": 5}'},
            "morphology": {"summary": "erosion/dilation/opening/closing", "value": '{"kernelSize": 5, "kernelShape": "ellipse", "iterations": 2}'},
            "threshold": {"summary": "binary/inverse/tozero/...", "value": '{"thresholdValue": 100, "maxValue": 255}'},
            "brightness": {"summary": "plus/minus", "value": '{"alpha": 1.2, "beta": 50}'},
        },
    )] = None,
) -> StreamingResponse:
    """이미지 처리"""

    # parameters JSON 파싱
    params_dict: dict[str, Any] | None = None
    if parameters is not None:
        try:
            params_dict = json.loads(parameters)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail=f"invalid parameters JSON: {exc}") from exc

    uploaded_file_bytes = await file.read()

    try:
        start = time.perf_counter()
        processed_image_bytes = process_image(
            prc_type=prc_type,
            image_bytes=uploaded_file_bytes,
            parameters=params_dict,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=exc.errors()) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return StreamingResponse(
        BytesIO(processed_image_bytes),
        media_type="image/png",
        headers={"X-Process-Time-Ms": f"{elapsed_ms:.2f}"},
    )


@router.post("/image-processing/save", tags=["img-processing"], response_model=FileSaveResponse)
async def img_processing_save(
    blob: Annotated[UploadFile, File(description="저장할 처리 완료 이미지 (image/png 또는 image/jpeg)")],
    prc_type: Annotated[PrcType, Form(alias="prcType", description="이미지에 적용된 처리 종류")],
    prc_ms: Annotated[float, Form(alias="prcMs", description="처리시간")]
) -> FileSaveResponse:
    """처리 이미지 저장"""

    # Python: 연산자 오버로딩
    # Path / "문자열"이면 Path.__truediv__()가 호출되어 경로 결합 연산자로 작동
    base = Path("uploads") / datetime.now().strftime("%Y-%m-%d")
    base.mkdir(parents=True, exist_ok=True)

    data = await blob.read()
    if blob.content_type not in ("image/png", "image/jpeg"):
        raise HTTPException(400, "unsupported content type")

    #### 파일쓰기 ####
    ext = ".png" if blob.content_type == "image/png" else ".jpg"
    saved_name = f"{uuid4().hex}{ext}"
    saved = base / saved_name
    saved.write_bytes(data)

    origin_nm = blob.filename or saved_name
    saved_path = str(saved).replace("\\", "/")

    #### DB 저장 ####
    try:
        inserted = insert_file(
            origin_nm=origin_nm,
            nm=saved_name,
            path=saved_path,
            mime_type=blob.content_type,
            size_bytes=len(data),
            options={"prcType": prc_type, "prcMs": prc_ms},
        )
    except Exception as exc:
        logger.exception("failed to persist file metadata")
        if saved.exists():
            saved.unlink()
        raise HTTPException(status_code=500, detail="failed to persist file metadata") from exc

    #### 응답 ####
    return FileSaveResponse(
        id=inserted["id"],
        origin_nm=origin_nm,
        nm=saved_name,
        path=saved_path,
        mime_type=blob.content_type,
        size_bytes=len(data),
        uploaded_at=inserted["uploaded_at"],
        options=FileSaveOptions(prc_type=prc_type),
    )


@router.post("/image-processing/upload", tags=["img-processing"], response_model=FileUploadResponse)
async def img_upload(
    file: Annotated[UploadFile, File(description="업로드할 원본 이미지 파일")],
) -> FileUploadResponse:
    """원본 이미지 파일 업로드 (동일 파일 중복 방지: content hash 기반)"""

    data = await file.read()
    if file.content_type not in ("image/png", "image/jpeg", "image/webp"):
        raise HTTPException(400, "unsupported content type")

    # 콘텐츠 해시 계산 → 기존 동일 파일이 있으면 즉시 반환
    content_hash = sha256(data).hexdigest()
    existing = find_file_by_hash(content_hash)
    if existing is not None:
        return FileUploadResponse(
            id=existing["id"],
            origin_nm=existing["origin_nm"],
            nm=existing["nm"],
            path=existing["path"],
            mime_type=existing["mime_type"],
            size_bytes=existing["size_bytes"],
            uploaded_at=existing["uploaded_at"],
        )

    ext = {
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/webp": ".webp",
    }[file.content_type]

    base = Path("uploads") / datetime.now().strftime("%Y-%m-%d")
    base.mkdir(parents=True, exist_ok=True)

    saved_name = f"{uuid4().hex}{ext}"
    saved = base / saved_name
    saved.write_bytes(data)

    origin_nm = file.filename or saved_name
    saved_path = str(saved).replace("\\", "/")

    try:
        inserted = insert_file(
            origin_nm=origin_nm,
            nm=saved_name,
            path=saved_path,
            mime_type=file.content_type,
            size_bytes=len(data),
            content_hash=content_hash,
            options={},
        )
    except Exception as exc:
        logger.exception("failed to persist file metadata")
        if saved.exists():
            saved.unlink()
        raise HTTPException(status_code=500, detail="failed to persist file metadata") from exc

    return FileUploadResponse(
        id=inserted["id"],
        origin_nm=origin_nm,
        nm=saved_name,
        path=saved_path,
        mime_type=file.content_type,
        size_bytes=len(data),
        uploaded_at=inserted["uploaded_at"],
    )


@router.post("/image-processing/batch", tags=["img-processing"])
async def img_processing_batch(
    file: Annotated[UploadFile, File(description="처리할 원본 이미지 파일")],
    steps: Annotated[str, Form(
        description='처리 단계 JSON 배열. 예: [{"prcType":"gaussianBlur","parameters":{"kernelSize":5}},{"prcType":"canny"}]',
    )],
) -> StreamingResponse:
    """노드리스트 기반 배치 이미지 처리. steps 순서대로 연쇄 적용한다."""

    try:
        steps_list: list[dict[str, Any]] = json.loads(steps)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"invalid steps JSON: {exc}") from exc

    if not isinstance(steps_list, list) or len(steps_list) == 0:
        raise HTTPException(status_code=400, detail="steps must be a non-empty array")

    uploaded_file_bytes = await file.read()

    try:
        result = process_image_batch(
            image_bytes=uploaded_file_bytes,
            steps=steps_list,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=exc.errors()) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    step_times = ",".join(
        f"{s.prc_type}:{s.execution_ms}" for s in result.steps
    )

    return StreamingResponse(
        BytesIO(result.image_bytes),
        media_type="image/png",
        headers={
            "X-Total-Process-Time-Ms": f"{result.total_execution_ms:.2f}",
            "X-Step-Times": step_times,
        },
    )


@router.post("/image-processing/batch-tree", tags=["img-processing"], response_model=TreeBatchResponse)
async def img_processing_batch_tree(
    file: Annotated[UploadFile, File(description="연산처리를 위한 입력 이미지")],
    steps: Annotated[str, Form(
        description='트리 형태 처리 단계 JSON 배열. 예: [{"nodeId":"n1","prcType":"gaussianBlur","parameters":{},"parentId":null}]',
    )],
    file_id: Annotated[str, Form(alias="fileId", description="원본 파일 ID (캐시 키 루트)")],
    full_size: Annotated[bool, Form(alias="fullSize", description="true이면 썸네일 대신 원본 해상도 반환")] = False,
) -> TreeBatchResponse:
    """트리 구조 배치 이미지 처리.

    parentId로 트리를 구성하며, 같은 parentId를 가진 노드들은 분기(비교) 처리된다.
    결과 이미지는 캐시 파일로 저장하고 URL을 반환한다.
    """

    try:
        steps_list: list[dict[str, Any]] = json.loads(steps)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"invalid steps JSON: {exc}") from exc

    if not isinstance(steps_list, list) or len(steps_list) == 0:
        raise HTTPException(status_code=400, detail="steps must be a non-empty array")

    # nodeId 필수 검증
    for i, step in enumerate(steps_list):
        if "nodeId" not in step:
            raise HTTPException(status_code=400, detail=f"steps[{i}] missing required field: nodeId")
        if "prcType" not in step:
            raise HTTPException(status_code=400, detail=f"steps[{i}] missing required field: prcType")

    uploaded_file_bytes = await file.read()

    try:
        result = process_image_batch_tree(
            image_bytes=uploaded_file_bytes,
            steps=steps_list,
            file_id=file_id,
            full_size=full_size,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=exc.errors()) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return TreeBatchResponse(
        total_execution_ms=result.total_execution_ms,
        results=[
            TreeNodeResultResponse(
                node_id=nr.node_id,
                image_url=nr.image_url,
                execution_ms=nr.execution_ms,
            )
            for nr in result.node_results
        ],
    )
