"""파일 목록 조회 API 테스트"""

from unittest.mock import patch

from httpx import AsyncClient


def _mock_page(items=None):
    return {
        "items": items or [],
        "has_more": False,
        "next_cursor_uploaded_at": None,
        "next_cursor_id": None,
    }


def _mock_file_item(**overrides):
    base = {
        "id": "test-uuid",
        "origin_nm": "photo.jpg",
        "nm": "abc123.jpg",
        "path": "uploads/2026-03-09/abc123.jpg",
        "mime_type": "image/jpeg",
        "size_bytes": 204800,
        "uploaded_at": "2026-03-09T12:00:00",
        "options": {},
    }
    base.update(overrides)
    return base


@patch("app.api.endpoints.file.list_files")
async def test_get_files_empty(mock_list, client: AsyncClient):
    """GET /api/files — 빈 목록"""
    mock_list.return_value = _mock_page()
    resp = await client.get("/api/files")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["hasMore"] is False


@patch("app.api.endpoints.file.list_files")
async def test_get_files_with_items(mock_list, client: AsyncClient):
    """GET /api/files — 항목 반환"""
    mock_list.return_value = _mock_page(items=[_mock_file_item()])
    resp = await client.get("/api/files")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["originNm"] == "photo.jpg"


@patch("app.api.endpoints.file.list_files")
async def test_get_files_mime_filter(mock_list, client: AsyncClient):
    """GET /api/files?mimeType=image/* — MIME 필터 전달 확인"""
    mock_list.return_value = _mock_page()
    await client.get("/api/files?mimeType=image/*")
    mock_list.assert_called_once()
    call_kwargs = mock_list.call_args.kwargs
    assert call_kwargs["mime_type"] == "image/*"


@patch("app.api.endpoints.file.list_files")
async def test_get_files_limit(mock_list, client: AsyncClient):
    """GET /api/files?limit=5 — limit 파라미터 전달 확인"""
    mock_list.return_value = _mock_page()
    await client.get("/api/files?limit=5")
    call_kwargs = mock_list.call_args.kwargs
    assert call_kwargs["limit"] == 5


async def test_get_files_invalid_limit(client: AsyncClient):
    """GET /api/files?limit=0 — 유효하지 않은 limit"""
    resp = await client.get("/api/files?limit=0")
    assert resp.status_code == 422


async def test_get_files_limit_too_large(client: AsyncClient):
    """GET /api/files?limit=200 — limit 초과"""
    resp = await client.get("/api/files?limit=200")
    assert resp.status_code == 422
