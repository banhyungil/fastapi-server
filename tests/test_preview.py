"""Preview API 테스트 (crop 기반 미리보기)"""

import json
import shutil
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np
from httpx import AsyncClient

TEMP_DIR = Path("uploads/test_preview")


def _create_test_image(width: int = 200, height: int = 150) -> str:
    """테스트용 이미지를 디스크에 저장하고 경로를 반환한다."""
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    img = np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)
    path = TEMP_DIR / "test_image.png"
    cv2.imwrite(str(path), img)
    return str(path).replace("\\", "/")


def _mock_file_row(path: str) -> dict:
    return {
        "id": 1,
        "origin_nm": "test.png",
        "nm": "test.png",
        "path": path,
        "mime_type": "image/png",
        "size_bytes": 1000,
        "uploaded_at": "2026-03-18T12:00:00",
        "options": {},
        "width": 200,
        "height": 150,
    }


def _cleanup():
    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR, ignore_errors=True)
    cache_dir = Path("uploads/cache/1/preview")
    if cache_dir.exists():
        shutil.rmtree(cache_dir, ignore_errors=True)


# ── POST /files/crop ───────────────────────────────────────────────────────


@patch("app.api.endpoints.files.find_file_by_id")
async def test_preview_crop(mock_find, client: AsyncClient):
    """POST /preview/crop — 정상 crop 생성"""
    path = _create_test_image(200, 150)
    mock_find.return_value = _mock_file_row(path)

    try:
        resp = await client.post(
            "/api/files/crop",
            data={
                "fileId": 1,
                "nodeSteps": "[]",
                "nodeId": "source",
                "viewport": json.dumps({"x": 10, "y": 10, "w": 100, "h": 80}),
                "padding": "20",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "cropId" in data
        assert "nodeImageUrl" in data
        assert data["width"] == 100
        assert data["height"] == 80

        # 캐시 파일 존재 확인
        cache_dir = Path("uploads/cache/1/preview")
        assert cache_dir.exists()
        crop_files = list(cache_dir.glob(f"{data['cropId']}*"))
        assert len(crop_files) == 2  # crop + node crop
    finally:
        _cleanup()


@patch("app.api.endpoints.files.find_file_by_id")
async def test_preview_crop_file_not_found(mock_find, client: AsyncClient):
    """POST /preview/crop — 파일 없음"""
    mock_find.return_value = None
    resp = await client.post(
        "/api/files/crop",
        data={
            "fileId": 999,
            "nodeSteps": "[]",
            "nodeId": "source",
            "viewport": json.dumps({"x": 0, "y": 0, "w": 100, "h": 100}),
        },
    )
    assert resp.status_code == 404


@patch("app.api.endpoints.files.find_file_by_id")
async def test_preview_crop_invalid_viewport(mock_find, client: AsyncClient):
    """POST /preview/crop — 잘못된 viewport JSON"""
    path = _create_test_image()
    mock_find.return_value = _mock_file_row(path)

    try:
        resp = await client.post(
            "/api/files/crop",
            data={
                "fileId": 1,
                "nodeSteps": "[]",
                "nodeId": "source",
                "viewport": "invalid-json",
            },
        )
        assert resp.status_code == 400
    finally:
        _cleanup()


# ── POST /preview/apply ──────────────────────────────────────────────────────


@patch("app.api.endpoints.files.find_file_by_id")
async def test_preview_apply(mock_find, client: AsyncClient):
    """POST /preview/apply — crop에 필터 적용"""
    path = _create_test_image(200, 150)
    mock_find.return_value = _mock_file_row(path)

    try:
        # 먼저 crop 생성
        viewport = {"x": 10, "y": 10, "w": 100, "h": 80}
        crop_resp = await client.post(
            "/api/files/crop",
            data={
                "fileId": 1,
                "nodeSteps": "[]",
                "nodeId": "source",
                "viewport": json.dumps(viewport),
                "padding": "20",
            },
        )
        assert crop_resp.status_code == 200
        crop_id = crop_resp.json()["cropId"]

        # 필터 적용
        temp_steps = [{"filterType": "gaussianBlur", "parameters": {"kernelSize": 5}}]
        apply_resp = await client.post(
            "/api/files/crop/apply",
            data={
                "fileId": 1,
                "cropId": crop_id,
                "tempSteps": json.dumps(temp_steps),
                "viewport": json.dumps(viewport),
                "padding": "20",
            },
        )
        assert apply_resp.status_code == 200
        assert apply_resp.headers["content-type"] == "application/json"
        data = apply_resp.json()
        assert "imageBase64" in data
        assert "executionMs" in data
    finally:
        _cleanup()


@patch("app.api.endpoints.files.find_file_by_id")
async def test_preview_apply_multiple_steps(mock_find, client: AsyncClient):
    """POST /preview/apply — 여러 필터 순차 적용"""
    path = _create_test_image(200, 150)
    mock_find.return_value = _mock_file_row(path)

    try:
        viewport = {"x": 10, "y": 10, "w": 100, "h": 80}
        crop_resp = await client.post(
            "/api/files/crop",
            data={
                "fileId": 1,
                "nodeSteps": "[]",
                "nodeId": "source",
                "viewport": json.dumps(viewport),
                "padding": "20",
            },
        )
        crop_id = crop_resp.json()["cropId"]

        temp_steps = [
            {"filterType": "gaussianBlur", "parameters": {"kernelSize": 5}},
            {"filterType": "canny", "parameters": {"threshold1": 50, "threshold2": 150}},
        ]
        apply_resp = await client.post(
            "/api/files/crop/apply",
            data={
                "fileId": 1,
                "cropId": crop_id,
                "tempSteps": json.dumps(temp_steps),
                "viewport": json.dumps(viewport),
                "padding": "20",
            },
        )
        assert apply_resp.status_code == 200
        assert apply_resp.headers["content-type"] == "application/json"
        assert "imageBase64" in apply_resp.json()
    finally:
        _cleanup()


async def test_preview_apply_invalid_crop_id(client: AsyncClient):
    """POST /preview/apply — 존재하지 않는 cropId"""
    resp = await client.post(
        "/api/files/crop/apply",
        data={
            "fileId": 1,
            "cropId": "nonexistent",
            "tempSteps": "[]",
            "viewport": json.dumps({"x": 0, "y": 0, "w": 100, "h": 100}),
        },
    )
    assert resp.status_code == 400


# ── DELETE /preview/crop ─────────────────────────────────────────────────────


@patch("app.api.endpoints.files.find_file_by_id")
async def test_preview_delete(mock_find, client: AsyncClient):
    """DELETE /preview/crop — 캐시 삭제"""
    path = _create_test_image(200, 150)
    mock_find.return_value = _mock_file_row(path)

    try:
        # crop 생성
        crop_resp = await client.post(
            "/api/files/crop",
            data={
                "fileId": 1,
                "nodeSteps": "[]",
                "nodeId": "source",
                "viewport": json.dumps({"x": 0, "y": 0, "w": 100, "h": 100}),
            },
        )
        crop_id = crop_resp.json()["cropId"]

        # 삭제
        del_resp = await client.delete(
            f"/api/files/crop/1/{crop_id}"
        )
        assert del_resp.status_code == 200
        assert del_resp.json()["detail"] == "deleted"

        # 캐시 파일 삭제 확인
        cache_dir = Path("uploads/cache/1/preview")
        crop_files = list(cache_dir.glob(f"{crop_id}*"))
        assert len(crop_files) == 0
    finally:
        _cleanup()
