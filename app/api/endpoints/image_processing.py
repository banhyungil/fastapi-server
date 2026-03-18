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

import cv2
import numpy as np

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import ValidationError

# 절대 import
from app.schemas.file import TFile, FileListResponse, FileSaveResponse, FileSaveOptions, FileUploadResponse, FileRenameRequest, PrcType, TreeBatchResponse, TreeNodeResultResponse, DziResponse, Viewport, PreviewCropResponse
from app.services.file_service import insert_file, list_files, find_file_by_hash, find_file_by_id, delete_file, rename_file
from app.schemas.image_processing import PARAM_MODELS
from app.services.image_processing_service import process_image, process_image_batch, process_image_batch_tree, generate_dzi_for_node, download_node_image, save_file_thumbnail, get_file_thumbnail_url
from app.services.preview_service import create_preview_crop, apply_preview_filter, delete_preview_crop

router = APIRouter()
logger = logging.getLogger(__name__)


def _get_image_dimensions(data: bytes) -> tuple[int, int]:
    """이미지 바이트에서 (width, height)를 추출한다."""
    arr = np.frombuffer(data, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("failed to decode image for dimension extraction")
    h, w = img.shape[:2]
    return w, h

@router.get("/image-processing", tags=["img-processing"], response_model=FileListResponse)
async def get_saved_images(
    limit: Annotated[int, Query(ge=1, le=100, description="반환할 최대 항목 수")] = 20,
    search: Annotated[str | None, Query(description="파일명 검색 (부분 일치)")] = None,
    min_size: Annotated[int | None, Query(alias="minSize", ge=0, description="최소 파일 크기 (bytes)")] = None,
    max_size: Annotated[int | None, Query(alias="maxSize", ge=0, description="최대 파일 크기 (bytes)")] = None,
    cursor_uploaded_at: Annotated[datetime | None, Query(alias="cursorUploadedAt", description="커서 기준 업로드 시각 (cursorId와 함께 제공)")] = None,
    cursor_id: Annotated[UUID | None, Query(alias="cursorId", description="커서 기준 파일 ID (cursorUploadedAt와 함께 제공)")] = None,
) -> FileListResponse:
    """처리 이미지 조회"""

    if (cursor_uploaded_at is None) != (cursor_id is None):
        raise HTTPException(status_code=400, detail="cursorUploadedAt and cursorId must be provided together")

    page = list_files(
        limit=limit,
        search=search,
        min_size=min_size,
        max_size=max_size,
        cursor_uploaded_at=cursor_uploaded_at,
        cursor_id=cursor_id,
    )

    items: list[TFile] = []
    for item in page["items"]:
        t_file = TFile.model_validate(item)
        t_file.thumbnail_url = get_file_thumbnail_url(str(item["id"]))
        items.append(t_file)

    return FileListResponse(
        items=items,
        has_more=page["has_more"],
        next_cursor_uploaded_at=page["next_cursor_uploaded_at"],
        next_cursor_id=page["next_cursor_id"],
    )


@router.delete("/image-processing/{file_id}", tags=["img-processing"])
async def delete_image(file_id: str) -> dict[str, str]:
    """이미지 파일 삭제 (DB 메타데이터 + 디스크 파일)"""
    try:
        delete_file(file_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"detail": "deleted"}


@router.patch("/image-processing/{file_id}", tags=["img-processing"], response_model=TFile)
async def rename_image(file_id: str, body: FileRenameRequest) -> TFile:
    """이미지 파일명(originNm) 수정"""
    try:
        updated = rename_file(file_id, body.origin_nm)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return TFile.model_validate(updated)


@router.get("/image-processing/thumbnail/{file_id}", tags=["img-processing"])
async def get_thumbnail(
    file_id: str,
    size: Annotated[int, Query(ge=32, le=400, description="썸네일 최대 변 크기 (px)")] = 200,
) -> StreamingResponse:
    """파일 ID에 해당하는 이미지를 지정 크기로 축소하여 반환한다."""
    import cv2
    import numpy as np

    file_row = find_file_by_id(file_id)
    if file_row is None:
        raise HTTPException(status_code=404, detail=f"file not found: {file_id}")

    file_path = Path(file_row["path"])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="file not found on disk")

    data = file_path.read_bytes()
    arr = np.frombuffer(data, dtype=np.uint8)
    image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(status_code=500, detail="failed to decode image")

    h, w = image.shape[:2]
    if max(h, w) > size:
        scale = size / max(h, w)
        image = cv2.resize(image, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

    success, encoded = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 80])
    if not success:
        raise HTTPException(status_code=500, detail="failed to encode thumbnail")

    return StreamingResponse(
        BytesIO(encoded.tobytes()),
        media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=86400"},
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

    #### 해상도 추출 ####
    width, height = _get_image_dimensions(data)

    #### DB 저장 ####
    try:
        inserted = insert_file(
            origin_nm=origin_nm,
            nm=saved_name,
            path=saved_path,
            mime_type=blob.content_type,
            size_bytes=len(data),
            options={"prcType": prc_type, "prcMs": prc_ms},
            width=width,
            height=height,
        )
    except Exception as exc:
        logger.exception("failed to persist file metadata")
        if saved.exists():
            saved.unlink()
        raise HTTPException(status_code=500, detail="failed to persist file metadata") from exc

    # 썸네일 미리 생성
    try:
        save_file_thumbnail(str(inserted["id"]), data)
    except Exception:
        logger.warning("failed to generate thumbnail for %s", inserted["id"])

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
        width=width,
        height=height,
    )


@router.post("/image-processing/upload", tags=["img-processing"], response_model=FileUploadResponse)
async def img_upload(
    file: Annotated[UploadFile, File(description="업로드할 원본 이미지 파일")],
) -> FileUploadResponse:
    """원본 이미지 파일 업로드 (동일 파일 중복 방지: content hash 기반)"""

    data = await file.read()
    if file.content_type not in ("image/png", "image/jpeg", "image/webp", "image/bmp", "image/tiff"):
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
            width=existing["width"],
            height=existing["height"],
        )

    ext = {
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/webp": ".webp",
        "image/bmp": ".bmp",
        "image/tiff": ".tif",
    }[file.content_type]

    base = Path("uploads") / datetime.now().strftime("%Y-%m-%d")
    base.mkdir(parents=True, exist_ok=True)

    saved_name = f"{uuid4().hex}{ext}"
    saved = base / saved_name
    saved.write_bytes(data)

    origin_nm = file.filename or saved_name
    saved_path = str(saved).replace("\\", "/")

    #### 해상도 추출 ####
    width, height = _get_image_dimensions(data)

    try:
        inserted = insert_file(
            origin_nm=origin_nm,
            nm=saved_name,
            path=saved_path,
            mime_type=file.content_type,
            size_bytes=len(data),
            content_hash=content_hash,
            options={},
            width=width,
            height=height,
        )
    except Exception as exc:
        logger.exception("failed to persist file metadata")
        if saved.exists():
            saved.unlink()
        raise HTTPException(status_code=500, detail="failed to persist file metadata") from exc

    # 썸네일 미리 생성
    try:
        save_file_thumbnail(str(inserted["id"]), data)
    except Exception:
        logger.warning("failed to generate thumbnail for %s", inserted["id"])

    return FileUploadResponse(
        id=inserted["id"],
        origin_nm=origin_nm,
        nm=saved_name,
        path=saved_path,
        mime_type=file.content_type,
        size_bytes=len(data),
        uploaded_at=inserted["uploaded_at"],
        width=width,
        height=height,
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
    file_id: Annotated[str, Form(alias="fileId", description="처리할 원본 이미지 파일 ID")],
    steps: Annotated[str, Form(
        description='트리 형태 처리 단계 JSON 배열. 예: [{"nodeId":"n1","prcType":"gaussianBlur","parameters":{},"parentId":null}]',
    )],
    thumbnail_size: Annotated[int | None, Form(alias="thumbnailSize", ge=50, le=800, description="썸네일 해상도 (px)")] = None,
) -> TreeBatchResponse:
    """트리 구조 배치 이미지 처리.

    parentId로 트리를 구성하며, 같은 parentId를 가진 노드들은 분기(비교) 처리된다.
    결과는 썸네일(base64 data URL)로 반환한다.
    """

    file_row = find_file_by_id(file_id)
    if file_row is None:
        raise HTTPException(status_code=404, detail=f"file not found: {file_id}")

    file_path = Path(file_row["path"])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="file not found on disk")

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

    image_bytes = file_path.read_bytes()

    try:
        result = process_image_batch_tree(
            image_bytes=image_bytes,
            steps=steps_list,
            thumbnail_size=thumbnail_size,
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


@router.post(
    "/image-processing/dzi/{file_id}",
    tags=["img-processing"],
    response_model=DziResponse,
)
async def create_dzi(
    file_id: str,
    steps: Annotated[str, Form(
        description='타겟 노드까지의 처리 단계 JSON 배열',
    )],
    node_id: Annotated[str, Form(alias="nodeId", description="DZI를 생성할 타겟 노드 ID")],
) -> DziResponse:
    """원본 이미지에 steps 체인을 적용하고, 타겟 노드의 DZI 타일(또는 원본 이미지)을 생성한다."""

    # 파일 경로 조회
    file_row = find_file_by_id(file_id)
    if file_row is None:
        raise HTTPException(status_code=404, detail=f"file not found: {file_id}")

    try:
        steps_list: list[dict[str, Any]] = json.loads(steps)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"invalid steps JSON: {exc}") from exc

    try:
        result = generate_dzi_for_node(
            file_path=file_row["path"],
            steps=steps_list,
            file_id=file_id,
            node_id=node_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return DziResponse(dzi_url=result.dzi_url, image_url=result.image_url)


@router.post("/image-processing/download/{file_id}", tags=["img-processing"])
async def download_node(
    file_id: str,
    steps: Annotated[str, Form(
        description='타겟 노드까지의 처리 단계 JSON 배열',
    )],
    node_id: Annotated[str, Form(alias="nodeId", description="다운로드할 타겟 노드 ID")],
) -> StreamingResponse:
    """원본 이미지에 steps 체인을 적용하고, 타겟 노드의 처리 결과를 PNG로 다운로드한다."""

    file_row = find_file_by_id(file_id)
    if file_row is None:
        raise HTTPException(status_code=404, detail=f"file not found: {file_id}")

    try:
        steps_list: list[dict[str, Any]] = json.loads(steps)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"invalid steps JSON: {exc}") from exc

    try:
        image_bytes = download_node_image(
            file_path=file_row["path"],
            steps=steps_list,
            node_id=node_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return StreamingResponse(
        BytesIO(image_bytes),
        media_type="image/png",
        headers={"Content-Disposition": f'attachment; filename="{node_id}.png"'},
    )


# ── Preview (crop 기반 미리보기) ──────────────────────────────────────────────


@router.post(
    "/image-processing/preview/crop",
    tags=["img-processing"],
    response_model=PreviewCropResponse,
)
async def preview_crop(
    file_id: Annotated[str, Form(alias="fileId", description="원본 파일 ID")],
    node_steps: Annotated[str, Form(alias="nodeSteps", description="해당 노드까지의 기존 steps JSON 배열")],
    node_id: Annotated[str, Form(alias="nodeId", description="대상 노드 ID")],
    viewport: Annotated[str, Form(description="crop 영역 JSON { x, y, w, h } (px)")],
    padding: Annotated[int, Form(ge=0, le=200, description="경계 아티팩트 방지 여유 영역 (px)")] = 50,
) -> PreviewCropResponse:
    """뷰포트 영역의 crop 이미지를 생성하고 캐시한다."""

    file_row = find_file_by_id(file_id)
    if file_row is None:
        raise HTTPException(status_code=404, detail=f"file not found: {file_id}")

    try:
        steps_list: list[dict[str, Any]] = json.loads(node_steps)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"invalid nodeSteps JSON: {exc}") from exc

    try:
        vp = Viewport.model_validate_json(viewport)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"invalid viewport JSON: {exc}") from exc

    try:
        result = create_preview_crop(
            file_path=file_row["path"],
            node_steps=steps_list,
            node_id=node_id,
            viewport={"x": vp.x, "y": vp.y, "w": vp.w, "h": vp.h},
            file_id=file_id,
            padding=padding,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return PreviewCropResponse(
        crop_id=result.crop_id,
        node_image_url=result.node_image_url,
        width=result.width,
        height=result.height,
    )


@router.post("/image-processing/preview/apply", tags=["img-processing"])
async def preview_apply(
    file_id: Annotated[str, Form(alias="fileId", description="원본 파일 ID")],
    crop_id: Annotated[str, Form(alias="cropId", description="crop 캐시 ID")],
    temp_steps: Annotated[str, Form(alias="tempSteps", description="임시 필터 steps JSON 배열")],
    viewport: Annotated[str, Form(description="crop 시 사용한 viewport JSON")],
    padding: Annotated[int, Form(ge=0, le=200, description="crop 시 사용한 padding")] = 50,
) -> StreamingResponse:
    """캐시된 crop 이미지에 tempSteps를 적용한 결과를 반환한다."""

    try:
        steps_list: list[dict[str, Any]] = json.loads(temp_steps)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"invalid tempSteps JSON: {exc}") from exc

    try:
        vp = Viewport.model_validate_json(viewport)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"invalid viewport JSON: {exc}") from exc

    try:
        result_bytes = apply_preview_filter(
            file_id=file_id,
            crop_id=crop_id,
            temp_steps=steps_list,
            viewport={"x": vp.x, "y": vp.y, "w": vp.w, "h": vp.h},
            padding=padding,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return StreamingResponse(BytesIO(result_bytes), media_type="image/png")


@router.delete("/image-processing/preview/crop/{file_id}/{crop_id}", tags=["img-processing"])
async def preview_delete(file_id: str, crop_id: str) -> dict[str, str]:
    """캐시된 preview crop 파일을 삭제한다."""
    delete_preview_crop(file_id, crop_id)
    return {"detail": "deleted"}
