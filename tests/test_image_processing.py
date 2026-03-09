"""이미지 처리 API 테스트"""

import json
from unittest.mock import patch

from httpx import AsyncClient


async def test_single_processing(client: AsyncClient, test_image_bytes: bytes):
    """POST /api/image-processing — 단일 필터 적용"""
    resp = await client.post(
        "/api/image-processing",
        data={"prcType": "gaussianBlur"},
        files={"file": ("test.png", test_image_bytes, "image/png")},
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"
    assert "X-Process-Time-Ms" in resp.headers


async def test_single_processing_with_params(client: AsyncClient, test_image_bytes: bytes):
    """POST /api/image-processing — 파라미터 포함 필터 적용"""
    params = json.dumps({"kernelSize": 7, "sigmaX": 1.5})
    resp = await client.post(
        "/api/image-processing",
        data={"prcType": "gaussianBlur", "parameters": params},
        files={"file": ("test.png", test_image_bytes, "image/png")},
    )
    assert resp.status_code == 200


async def test_single_processing_invalid_prc_type(client: AsyncClient, test_image_bytes: bytes):
    """POST /api/image-processing — 지원하지 않는 prcType"""
    resp = await client.post(
        "/api/image-processing",
        data={"prcType": "invalidFilter"},
        files={"file": ("test.png", test_image_bytes, "image/png")},
    )
    assert resp.status_code == 422


async def test_batch_processing(client: AsyncClient, test_image_bytes: bytes):
    """POST /api/image-processing/batch — 순차 배치 처리"""
    steps = json.dumps([
        {"prcType": "gaussianBlur", "parameters": {"kernelSize": 5}},
        {"prcType": "sobel", "parameters": {"kernelSize": 3, "dx": 1, "dy": 0}},
    ])
    resp = await client.post(
        "/api/image-processing/batch",
        data={"steps": steps},
        files={"file": ("test.png", test_image_bytes, "image/png")},
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"
    assert "X-Total-Process-Time-Ms" in resp.headers


async def test_batch_tree_processing(client: AsyncClient, test_image_bytes: bytes):
    """POST /api/image-processing/batch-tree — 트리 배치 처리"""
    steps = json.dumps([
        {"nodeId": "n1", "prcType": "gaussianBlur", "parameters": {"kernelSize": 5}, "parentId": None},
        {"nodeId": "n2", "prcType": "sobel", "parameters": {"kernelSize": 3, "dx": 1, "dy": 0}, "parentId": "n1"},
    ])
    resp = await client.post(
        "/api/image-processing/batch-tree",
        data={"steps": steps, "fileId": "test-file-id"},
        files={"file": ("test.png", test_image_bytes, "image/png")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["totalExecutionMs"] >= 0
    assert len(data["results"]) == 2
    assert data["results"][0]["nodeId"] == "n1"
    assert data["results"][1]["nodeId"] == "n2"
    assert data["results"][0]["imageUrl"].startswith("/uploads/cache/")
    # 100x100 이미지이므로 DZI 생성 안 됨
    assert data["results"][0]["dziUrl"] is None


async def test_batch_tree_branching(client: AsyncClient, test_image_bytes: bytes):
    """POST /api/image-processing/batch-tree — 분기(sibling) 처리"""
    steps = json.dumps([
        {"nodeId": "root", "prcType": "blur", "parameters": {"kernelSize": 3}, "parentId": None},
        {"nodeId": "branch-a", "prcType": "sobel", "parameters": {}, "parentId": "root"},
        {"nodeId": "branch-b", "prcType": "canny", "parameters": {"threshold1": 100, "threshold2": 200}, "parentId": "root"},
    ])
    resp = await client.post(
        "/api/image-processing/batch-tree",
        data={"steps": steps, "fileId": "test-branch"},
        files={"file": ("test.png", test_image_bytes, "image/png")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["results"]) == 3
    node_ids = {r["nodeId"] for r in data["results"]}
    assert node_ids == {"root", "branch-a", "branch-b"}


async def test_batch_tree_empty_steps(client: AsyncClient, test_image_bytes: bytes):
    """POST /api/image-processing/batch-tree — 빈 steps 배열"""
    resp = await client.post(
        "/api/image-processing/batch-tree",
        data={"steps": "[]", "fileId": "test-empty"},
        files={"file": ("test.png", test_image_bytes, "image/png")},
    )
    assert resp.status_code == 400


async def test_batch_tree_missing_node_id(client: AsyncClient, test_image_bytes: bytes):
    """POST /api/image-processing/batch-tree — nodeId 누락"""
    steps = json.dumps([{"prcType": "blur", "parameters": {}, "parentId": None}])
    resp = await client.post(
        "/api/image-processing/batch-tree",
        data={"steps": steps, "fileId": "test-missing"},
        files={"file": ("test.png", test_image_bytes, "image/png")},
    )
    assert resp.status_code == 400
    assert "nodeId" in resp.json()["detail"]


async def test_upload_image(client: AsyncClient, test_image_bytes: bytes):
    """POST /api/image-processing/upload — 이미지 업로드 (DB mock)"""
    mock_return = {
        "id": "test-uuid",
        "uploaded_at": "2026-03-09T12:00:00",
    }
    with (
        patch("app.api.endpoints.image_processing.find_file_by_hash", return_value=None),
        patch("app.api.endpoints.image_processing.insert_file", return_value=mock_return),
    ):
        resp = await client.post(
            "/api/image-processing/upload",
            files={"file": ("test.png", test_image_bytes, "image/png")},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "test-uuid"
    assert data["mimeType"] == "image/png"
    assert data["originNm"] == "test.png"


async def test_upload_duplicate_image(client: AsyncClient, test_image_bytes: bytes):
    """POST /api/image-processing/upload — 중복 파일 업로드 시 기존 레코드 반환"""
    existing = {
        "id": "existing-uuid",
        "origin_nm": "original.png",
        "nm": "saved.png",
        "path": "uploads/2026-03-09/saved.png",
        "mime_type": "image/png",
        "size_bytes": 1234,
        "uploaded_at": "2026-03-09T12:00:00",
    }
    with patch("app.api.endpoints.image_processing.find_file_by_hash", return_value=existing):
        resp = await client.post(
            "/api/image-processing/upload",
            files={"file": ("test.png", test_image_bytes, "image/png")},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "existing-uuid"


async def test_get_filter_params(client: AsyncClient):
    """GET /api/image-processing/params/{prc_type} — 필터 파라미터 스키마 조회"""
    resp = await client.get("/api/image-processing/params/gaussianBlur")
    assert resp.status_code == 200
    data = resp.json()
    assert data["prcType"] == "gaussianBlur"
    assert "schema" in data


async def test_get_all_filter_params(client: AsyncClient):
    """GET /api/image-processing/params — 전체 필터 스키마 조회"""
    resp = await client.get("/api/image-processing/params")
    assert resp.status_code == 200
    data = resp.json()
    assert "gaussianBlur" in data
    assert "sobel" in data
