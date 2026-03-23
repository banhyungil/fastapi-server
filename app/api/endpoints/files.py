"""파일 관리, 이미지 처리, 미리보기, DZI, 다운로드 엔드포인트."""

import base64
import json
import logging
import time
from hashlib import sha256
from io import BytesIO
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any
from uuid import uuid4, UUID

import cv2
import numpy as np
from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import ValidationError

from app.schemas.file import (
    TFile, FileListResponse, FileSaveResponse, FileSaveOptions,
    FileUploadResponse, FileRenameRequest, FilterType,
    TreeBatchResponse, TreeNodeResultResponse,
    DziResponse, Viewport, PreviewCropResponse,
)
from app.services.files_service import (
    insert_file, list_files, find_file_by_hash, find_file_by_id,
    delete_file, rename_file,
    process_image, process_image_batch_tree,
)
from app.services.thumbnails import save_file_thumbnail, get_file_thumbnail_url
from app.services.dzi import generate_dzi_for_node, download_node_image
from app.services.crop import (
    create_preview_crop, apply_preview_filter,
    apply_preview_filter_all, delete_preview_crop,
)

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


@router.get("/files", tags=["files"], response_model=FileListResponse)
async def get_saved_images(
    limit: Annotated[int, Query(ge=1, le=100, description="반환할 최대 항목 수")] = 20,
    search: Annotated[str | None, Query(description="파일명 검색 (부분 일치)")] = None,
    min_size: Annotated[int | None, Query(alias="minSize", ge=0, description="최소 파일 크기 (bytes)")] = None,
    max_size: Annotated[int | None, Query(alias="maxSize", ge=0, description="최대 파일 크기 (bytes)")] = None,
    cursor_uploaded_at: Annotated[datetime | None, Query(alias="cursorUploadedAt", description="커서 기준 업로드 시각")] = None,
    cursor_id: Annotated[UUID | None, Query(alias="cursorId", description="커서 기준 파일 ID")] = None,
) -> FileListResponse:
    """처리 이미지 조회"""
    if (cursor_uploaded_at is None) != (cursor_id is None):
        raise HTTPException(status_code=400, detail="cursorUploadedAt and cursorId must be provided together")

    page = list_files(
        limit=limit, search=search, min_size=min_size, max_size=max_size,
        cursor_uploaded_at=cursor_uploaded_at, cursor_id=cursor_id,
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


@router.delete("/files/{file_id}", tags=["files"])
async def delete_image(file_id: str) -> dict[str, str]:
    """이미지 파일 삭제 (DB 메타데이터 + 디스크 파일)"""
    try:
        delete_file(file_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"detail": "deleted"}


@router.patch("/files/{file_id}", tags=["files"], response_model=TFile)
async def rename_image(file_id: str, body: FileRenameRequest) -> TFile:
    """이미지 파일명(originNm) 수정"""
    try:
        updated = rename_file(file_id, body.origin_nm)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return TFile.model_validate(updated)


@router.get("/files/thumbnail/{file_id}", tags=["files"])
async def get_thumbnail(
    file_id: str,
    size: Annotated[int, Query(ge=32, le=400, description="썸네일 최대 변 크기 (px)")] = 200,
) -> StreamingResponse:
    """파일 ID에 해당하는 이미지를 지정 크기로 축소하여 반환한다."""
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


@router.post("/files/save", tags=["files"], response_model=FileSaveResponse)
async def img_processing_save(
    blob: Annotated[UploadFile, File(description="저장할 처리 완료 이미지")],
    filter_type: Annotated[FilterType, Form(alias="filterType", description="이미지에 적용된 처리 종류")],
    prc_ms: Annotated[float, Form(alias="prcMs", description="처리시간")],
) -> FileSaveResponse:
    """처리 이미지 저장"""
    base = Path("uploads") / datetime.now().strftime("%Y-%m-%d")
    base.mkdir(parents=True, exist_ok=True)

    data = await blob.read()
    if blob.content_type not in ("image/png", "image/jpeg"):
        raise HTTPException(400, "unsupported content type")

    ext = ".png" if blob.content_type == "image/png" else ".jpg"
    saved_name = f"{uuid4().hex}{ext}"
    saved = base / saved_name
    saved.write_bytes(data)

    origin_nm = blob.filename or saved_name
    saved_path = str(saved).replace("\\", "/")
    width, height = _get_image_dimensions(data)

    try:
        inserted = insert_file(
            origin_nm=origin_nm, nm=saved_name, path=saved_path,
            mime_type=blob.content_type, size_bytes=len(data),
            options={"filterType": filter_type, "prcMs": prc_ms},
            width=width, height=height,
        )
    except Exception as exc:
        logger.exception("failed to persist file metadata")
        if saved.exists():
            saved.unlink()
        raise HTTPException(status_code=500, detail="failed to persist file metadata") from exc

    try:
        save_file_thumbnail(str(inserted["id"]), data)
    except Exception:
        logger.warning("failed to generate thumbnail for %s", inserted["id"])

    return FileSaveResponse(
        id=inserted["id"], origin_nm=origin_nm, nm=saved_name,
        path=saved_path, mime_type=blob.content_type, size_bytes=len(data),
        uploaded_at=inserted["uploaded_at"],
        options=FileSaveOptions(filter_type=filter_type),
        width=width, height=height,
    )


@router.post("/files/upload", tags=["files"], response_model=FileUploadResponse)
async def img_upload(
    file: Annotated[UploadFile, File(description="업로드할 원본 이미지 파일")],
) -> FileUploadResponse:
    """원본 이미지 파일 업로드 (동일 파일 중복 방지: content hash 기반)"""
    data = await file.read()
    if file.content_type not in ("image/png", "image/jpeg", "image/webp", "image/bmp", "image/tiff"):
        raise HTTPException(400, "unsupported content type")

    content_hash = sha256(data).hexdigest()
    existing = find_file_by_hash(content_hash)
    if existing is not None:
        return FileUploadResponse(
            id=existing["id"], origin_nm=existing["origin_nm"], nm=existing["nm"],
            path=existing["path"], mime_type=existing["mime_type"],
            size_bytes=existing["size_bytes"], uploaded_at=existing["uploaded_at"],
            width=existing["width"], height=existing["height"],
        )

    ext = {
        "image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp",
        "image/bmp": ".bmp", "image/tiff": ".tif",
    }[file.content_type]

    base = Path("uploads") / datetime.now().strftime("%Y-%m-%d")
    base.mkdir(parents=True, exist_ok=True)

    saved_name = f"{uuid4().hex}{ext}"
    saved = base / saved_name
    saved.write_bytes(data)

    origin_nm = file.filename or saved_name
    saved_path = str(saved).replace("\\", "/")
    width, height = _get_image_dimensions(data)

    try:
        inserted = insert_file(
            origin_nm=origin_nm, nm=saved_name, path=saved_path,
            mime_type=file.content_type, size_bytes=len(data),
            content_hash=content_hash, options={},
            width=width, height=height,
        )
    except Exception as exc:
        logger.exception("failed to persist file metadata")
        if saved.exists():
            saved.unlink()
        raise HTTPException(status_code=500, detail="failed to persist file metadata") from exc

    try:
        save_file_thumbnail(str(inserted["id"]), data)
    except Exception:
        logger.warning("failed to generate thumbnail for %s", inserted["id"])

    return FileUploadResponse(
        id=inserted["id"], origin_nm=origin_nm, nm=saved_name,
        path=saved_path, mime_type=file.content_type, size_bytes=len(data),
        uploaded_at=inserted["uploaded_at"], width=width, height=height,
    )


# ── 이미지 처리 ──────────────────────────────────────────────────────────────


@router.post("/files/process", tags=["files"])
async def file_process(
    file: Annotated[UploadFile, File(description="처리할 원본 이미지 파일")],
    filter_type: Annotated[FilterType, Form(alias="filterType", description="적용할 이미지 처리 종류")],
    parameters: Annotated[str | None, Form(description="필터별 파라미터 JSON 문자열")] = None,
) -> StreamingResponse:
    """단일 필터 이미지 처리"""
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
            filter_type=filter_type, image_bytes=uploaded_file_bytes, parameters=params_dict,
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


@router.post("/files/process/batch-tree", tags=["files"], response_model=TreeBatchResponse)
async def file_process_batch_tree(
    file_id: Annotated[str, Form(alias="fileId", description="처리할 원본 이미지 파일 ID")],
    steps: Annotated[str, Form(description="트리 형태 처리 단계 JSON 배열")],
    thumbnail_size: Annotated[int | None, Form(alias="thumbnailSize", ge=50, le=800, description="썸네일 해상도 (px)")] = None,
    crop_id: Annotated[str | None, Form(alias="cropId", description="crop 캐시 ID (지정 시 crop 이미지 기준으로 처리)")] = None,
    return_node_ids: Annotated[str | None, Form(alias="returnNodeIds", description="이미지 반환할 노드 ID 목록 (JSON 배열, 미지정 시 전체)")] = None,
) -> TreeBatchResponse:
    """트리 구조 배치 이미지 처리."""
    file_row = find_file_by_id(file_id)
    if file_row is None:
        raise HTTPException(status_code=404, detail=f"file not found: {file_id}")

    try:
        steps_list: list[dict[str, Any]] = json.loads(steps)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"invalid steps JSON: {exc}") from exc

    if not isinstance(steps_list, list) or len(steps_list) == 0:
        raise HTTPException(status_code=400, detail="steps must be a non-empty array")

    for i, step in enumerate(steps_list):
        if "nodeId" not in step:
            raise HTTPException(status_code=400, detail=f"steps[{i}] missing required field: nodeId")
        if "filterType" not in step:
            raise HTTPException(status_code=400, detail=f"steps[{i}] missing required field: filterType")

    # cropId가 있으면 crop 캐시에서, 없으면 원본 파일에서 이미지 로드
    if crop_id:
        from app.services.cache import CACHE_DIR
        crop_path = CACHE_DIR / file_id / "preview" / f"{crop_id}.png"
        if not crop_path.exists():
            raise HTTPException(status_code=404, detail=f"crop not found: {crop_id}")
        image_bytes = crop_path.read_bytes()
    else:
        file_path = Path(file_row["path"])
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="file not found on disk")
        image_bytes = file_path.read_bytes()

    try:
        parsed_return_ids: set[str] | None = None
        if return_node_ids:
            try:
                ids_list = json.loads(return_node_ids)
                parsed_return_ids = set(ids_list) if isinstance(ids_list, list) else None
            except json.JSONDecodeError:
                pass

        result = process_image_batch_tree(
            image_bytes=image_bytes, steps=steps_list, thumbnail_size=thumbnail_size,
            return_node_ids=parsed_return_ids,
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
                node_id=nr.node_id, image_url=nr.image_url, execution_ms=nr.execution_ms,
                width=nr.width, height=nr.height,
            )
            for nr in result.node_results
        ],
    )


# ── DZI / Download ────────────────────────────────────────────────────────────


@router.post("/files/dzi/{file_id}", tags=["files"], response_model=DziResponse)
async def create_dzi(
    file_id: str,
    steps: Annotated[str, Form(description="타겟 노드까지의 처리 단계 JSON 배열")],
    node_id: Annotated[str, Form(alias="nodeId", description="DZI를 생성할 타겟 노드 ID")],
) -> DziResponse:
    """원본 이미지에 steps 체인을 적용하고, 타겟 노드의 DZI 타일(또는 원본 이미지)을 생성한다."""
    file_row = find_file_by_id(file_id)
    if file_row is None:
        raise HTTPException(status_code=404, detail=f"file not found: {file_id}")

    try:
        steps_list: list[dict[str, Any]] = json.loads(steps)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"invalid steps JSON: {exc}") from exc

    try:
        result = generate_dzi_for_node(
            file_path=file_row["path"], steps=steps_list,
            file_id=file_id, node_id=node_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return DziResponse(dzi_url=result.dzi_url, image_url=result.image_url)


@router.post("/files/download/{file_id}", tags=["files"])
async def download_node(
    file_id: str,
    steps: Annotated[str, Form(description="타겟 노드까지의 처리 단계 JSON 배열")],
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
            file_path=file_row["path"], steps=steps_list, node_id=node_id,
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


# ── Crop (crop 기반 미리보기) ──────────────────────────────────────────────────


@router.post("/files/crop", tags=["files"], response_model=PreviewCropResponse)
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
            file_path=file_row["path"], node_steps=steps_list,
            node_id=node_id, viewport={"x": vp.x, "y": vp.y, "w": vp.w, "h": vp.h},
            file_id=file_id, padding=padding,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return PreviewCropResponse(
        crop_id=result.crop_id, node_image_url=result.node_image_url,
        width=result.width, height=result.height,
    )


@router.post("/files/crop/apply", tags=["files"])
async def preview_apply(
    file_id: Annotated[str, Form(alias="fileId", description="원본 파일 ID")],
    crop_id: Annotated[str, Form(alias="cropId", description="crop 캐시 ID")],
    temp_steps: Annotated[str, Form(alias="tempSteps", description="임시 필터 steps JSON 배열")],
    viewport: Annotated[str, Form(description="crop 시 사용한 viewport JSON")],
    padding: Annotated[int, Form(ge=0, le=200, description="crop 시 사용한 padding")] = 50,
) -> dict[str, Any]:
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
        start = time.perf_counter()
        result_bytes = apply_preview_filter(
            file_id=file_id, crop_id=crop_id, temp_steps=steps_list,
            viewport={"x": vp.x, "y": vp.y, "w": vp.w, "h": vp.h},
            padding=padding,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "imageBase64": base64.b64encode(result_bytes).decode(),
        "executionMs": round(elapsed_ms, 2),
    }


@router.post("/files/crop/apply-all", tags=["files"])
async def preview_apply_all(
    file_id: Annotated[str, Form(alias="fileId", description="원본 파일 ID")],
    crop_id: Annotated[str, Form(alias="cropId", description="crop 캐시 ID")],
    temp_steps: Annotated[str, Form(alias="tempSteps", description="임시 필터 steps JSON 배열")],
    viewport: Annotated[str, Form(description="crop 시 사용한 viewport JSON")],
    padding: Annotated[int, Form(ge=0, le=200, description="crop 시 사용한 padding")] = 50,
) -> list[dict[str, Any]]:
    """캐시된 crop 이미지에 tempSteps를 적용하고 각 step별 중간 결과를 반환한다."""
    try:
        steps_list: list[dict[str, Any]] = json.loads(temp_steps)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"invalid tempSteps JSON: {exc}") from exc

    try:
        vp = Viewport.model_validate_json(viewport)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"invalid viewport JSON: {exc}") from exc

    try:
        results = apply_preview_filter_all(
            file_id=file_id, crop_id=crop_id, temp_steps=steps_list,
            viewport={"x": vp.x, "y": vp.y, "w": vp.w, "h": vp.h},
            padding=padding,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return [
        {
            "filterType": r.filter_type,
            "imageBase64": base64.b64encode(r.image_bytes).decode(),
            "executionMs": r.execution_ms,
        }
        for r in results
    ]


@router.delete("/files/crop/{file_id}/{crop_id}", tags=["files"])
async def preview_delete(file_id: str, crop_id: str) -> dict[str, str]:
    """캐시된 preview crop 파일을 삭제한다."""
    delete_preview_crop(file_id, crop_id)
    return {"detail": "deleted"}
