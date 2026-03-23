"""파일 CRUD + 이미지 처리 오케스트레이션 서비스."""

import time
from datetime import datetime
from pathlib import Path
from typing import Any, Unpack
from uuid import UUID

import cv2
import numpy as np

from app.schemas.file import FilterType
from app.schemas.image_processing import PARAM_MODELS
from app.repos.files_repo import (
    FileRow, FileRowInput, FileRowPage, InsertedFileMeta,
    insert_file_row, get_file_list, find_by_content_hash,
    find_by_id, delete_by_id, update_origin_nm,
)
from app.services.operations import OPERATIONS
from app.services.thumbnails import delete_file_thumbnail, encode_base64_thumbnail, THUMBNAIL_SIZE


# ── 파일 CRUD ─────────────────────────────────────────────────────────────────


def insert_file(**kwargs: Unpack[FileRowInput]) -> InsertedFileMeta:
    return insert_file_row(**kwargs)


def find_file_by_id(file_id: str) -> FileRow | None:
    return find_by_id(file_id)


def find_file_by_hash(content_hash: str) -> FileRow | None:
    return find_by_content_hash(content_hash)


def list_files(
    *,
    limit: int,
    mime_type: str | None = None,
    search: str | None = None,
    min_size: int | None = None,
    max_size: int | None = None,
    cursor_uploaded_at: datetime | None = None,
    cursor_id: UUID | None = None,
) -> FileRowPage:
    return get_file_list(
        limit=limit, mime_type=mime_type, search=search,
        min_size=min_size, max_size=max_size,
        cursor_uploaded_at=cursor_uploaded_at, cursor_id=cursor_id,
    )


def delete_file(file_id: str) -> FileRow:
    """파일 메타데이터 삭제 + 디스크 파일 삭제"""
    deleted = delete_by_id(file_id)
    if deleted is None:
        raise ValueError(f"file not found: {file_id}")

    disk_path = Path(deleted["path"])
    if disk_path.exists():
        disk_path.unlink()

    delete_file_thumbnail(str(deleted["id"]))

    return deleted


def rename_file(file_id: str, origin_nm: str) -> FileRow:
    """파일명(origin_nm) 수정"""
    updated = update_origin_nm(file_id, origin_nm)
    if updated is None:
        raise ValueError(f"file not found: {file_id}")
    return updated


# ── 단일 처리 ─────────────────────────────────────────────────────────────────


def process_image(
    filter_type: FilterType,
    image_bytes: bytes,
    parameters: dict[str, Any] | None = None,
) -> bytes:
    if not image_bytes:
        raise ValueError("empty image payload")

    image_array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("invalid image payload")

    op = OPERATIONS.get(filter_type)
    if op is None:
        raise ValueError(f"unsupported filterType: {filter_type}")

    param_cls = PARAM_MODELS[filter_type]
    params = param_cls.model_validate(parameters or {})
    processed = op(image, params)

    success, encoded = cv2.imencode(".png", processed)
    if not success:
        raise RuntimeError("failed to encode processed image")

    return encoded.tobytes()


# ── 트리 배치 처리 ────────────────────────────────────────────────────────────


class TreeNodeResult:
    __slots__ = ("node_id", "image_url", "execution_ms")

    def __init__(self, node_id: str, image_url: str, execution_ms: float) -> None:
        self.node_id = node_id
        self.image_url = image_url
        self.execution_ms = execution_ms


class TreeBatchResult:
    __slots__ = ("node_results", "total_execution_ms")

    def __init__(self, node_results: list[TreeNodeResult], total_execution_ms: float) -> None:
        self.node_results = node_results
        self.total_execution_ms = total_execution_ms


def process_image_batch_tree(
    image_bytes: bytes,
    steps: list[dict[str, Any]],
    *,
    thumbnail_size: int | None = None,
    return_node_ids: set[str] | None = None,
) -> TreeBatchResult:
    """트리 구조의 steps를 DFS로 순회하며 이미지를 처리한다."""
    if not image_bytes:
        raise ValueError("empty image payload")

    image_array = np.frombuffer(image_bytes, dtype=np.uint8)
    root_image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    if root_image is None:
        raise ValueError("invalid image payload")

    children_map: dict[str | None, list[dict[str, Any]]] = {}
    for step in steps:
        parent_id = step.get("parentId")
        children_map.setdefault(parent_id, []).append(step)

    node_images: dict[str, np.ndarray] = {}
    node_results: list[TreeNodeResult] = []
    total_start = time.perf_counter()

    stack: list[tuple[dict[str, Any], np.ndarray]] = []
    roots = children_map.get(None, [])
    for step in reversed(roots):
        stack.append((step, root_image))

    while stack:
        step, parent_image = stack.pop()

        node_id: str = step["nodeId"]
        filter_type: FilterType = step["filterType"]
        parameters: dict[str, Any] = step.get("parameters", {})

        op = OPERATIONS.get(filter_type)
        if op is None:
            raise ValueError(f"unsupported filterType: {filter_type}")

        param_cls = PARAM_MODELS[filter_type]
        params = param_cls.model_validate(parameters)

        step_start = time.perf_counter()
        result_image = op(parent_image, params)
        step_ms = (time.perf_counter() - step_start) * 1000

        node_images[node_id] = result_image

        # return_node_ids가 지정된 경우 해당 노드만 이미지 인코딩 (네트워크 절약)
        if return_node_ids is None or node_id in return_node_ids:
            thumb_px = thumbnail_size or THUMBNAIL_SIZE
            image_64_url = encode_base64_thumbnail(result_image, thumb_px)
        else:
            image_64_url = ""

        node_results.append(TreeNodeResult(
            node_id=node_id, image_url=image_64_url, execution_ms=round(step_ms, 2),
        ))

        children = children_map.get(node_id, [])
        for child in reversed(children):
            stack.append((child, result_image))

    total_ms = (time.perf_counter() - total_start) * 1000

    return TreeBatchResult(
        node_results=node_results, total_execution_ms=round(total_ms, 2),
    )
