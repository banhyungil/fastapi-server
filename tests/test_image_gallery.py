"""이미지 갤러리 API 테스트 (검색, 삭제, 파일명 수정)"""

from unittest.mock import patch

from httpx import AsyncClient


def _mock_page(items=None):
    return {
        "items": items or [],
        "has_more": False,
        "next_cursor_uploaded_at": None,
        "next_cursor_id": None,
    }


def _mock_file_row(**overrides):
    base = {
        "id": "aaaa-bbbb-cccc-dddd",
        "origin_nm": "sunset.jpg",
        "nm": "abc123.jpg",
        "path": "uploads/2026-03-13/abc123.jpg",
        "mime_type": "image/jpeg",
        "size_bytes": 204800,
        "uploaded_at": "2026-03-13T12:00:00",
        "options": {},
    }
    base.update(overrides)
    return base


# ── 검색 (GET /api/image-processing) ──────────────────────────────────────────


@patch("app.api.endpoints.image_processing.generate_thumbnail_base64", return_value=None)
@patch("app.api.endpoints.image_processing.list_files")
async def test_search_by_filename(mock_list, _mock_thumb, client: AsyncClient):
    """GET /api/image-processing?search=sunset — 파일명 검색 파라미터 전달"""
    mock_list.return_value = _mock_page(items=[_mock_file_row()])
    resp = await client.get("/api/image-processing?search=sunset")
    assert resp.status_code == 200
    call_kwargs = mock_list.call_args.kwargs
    assert call_kwargs["search"] == "sunset"


@patch("app.api.endpoints.image_processing.generate_thumbnail_base64", return_value=None)
@patch("app.api.endpoints.image_processing.list_files")
async def test_search_by_size_range(mock_list, _mock_thumb, client: AsyncClient):
    """GET /api/image-processing?minSize=1000&maxSize=500000 — 용량 필터"""
    mock_list.return_value = _mock_page()
    resp = await client.get("/api/image-processing?minSize=1000&maxSize=500000")
    assert resp.status_code == 200
    call_kwargs = mock_list.call_args.kwargs
    assert call_kwargs["min_size"] == 1000
    assert call_kwargs["max_size"] == 500000


@patch("app.api.endpoints.image_processing.generate_thumbnail_base64", return_value=None)
@patch("app.api.endpoints.image_processing.list_files")
async def test_search_combined(mock_list, _mock_thumb, client: AsyncClient):
    """검색어 + 용량 필터 동시 사용"""
    mock_list.return_value = _mock_page()
    resp = await client.get("/api/image-processing?search=photo&minSize=0&maxSize=1048576")
    assert resp.status_code == 200
    call_kwargs = mock_list.call_args.kwargs
    assert call_kwargs["search"] == "photo"
    assert call_kwargs["min_size"] == 0
    assert call_kwargs["max_size"] == 1048576


@patch("app.api.endpoints.image_processing.generate_thumbnail_base64", return_value=None)
@patch("app.api.endpoints.image_processing.list_files")
async def test_search_no_params(mock_list, _mock_thumb, client: AsyncClient):
    """검색 파라미터 없이 호출 시 None 전달"""
    mock_list.return_value = _mock_page()
    resp = await client.get("/api/image-processing")
    assert resp.status_code == 200
    call_kwargs = mock_list.call_args.kwargs
    assert call_kwargs["search"] is None
    assert call_kwargs["min_size"] is None
    assert call_kwargs["max_size"] is None


# ── 삭제 (DELETE /api/image-processing/{file_id}) ────────────────────────────


@patch("app.api.endpoints.image_processing.delete_file")
async def test_delete_success(mock_delete, client: AsyncClient):
    """DELETE /api/image-processing/{id} — 정상 삭제"""
    mock_delete.return_value = _mock_file_row()
    resp = await client.delete("/api/image-processing/aaaa-bbbb-cccc-dddd")
    assert resp.status_code == 200
    assert resp.json()["detail"] == "deleted"
    mock_delete.assert_called_once_with("aaaa-bbbb-cccc-dddd")


@patch("app.api.endpoints.image_processing.delete_file")
async def test_delete_not_found(mock_delete, client: AsyncClient):
    """DELETE /api/image-processing/{id} — 존재하지 않는 파일"""
    mock_delete.side_effect = ValueError("file not found: unknown-id")
    resp = await client.delete("/api/image-processing/unknown-id")
    assert resp.status_code == 404


# ── 파일명 수정 (PATCH /api/image-processing/{file_id}) ──────────────────────


@patch("app.api.endpoints.image_processing.rename_file")
async def test_rename_success(mock_rename, client: AsyncClient):
    """PATCH /api/image-processing/{id} — 정상 파일명 수정"""
    mock_rename.return_value = _mock_file_row(origin_nm="new_name.jpg")
    resp = await client.patch(
        "/api/image-processing/aaaa-bbbb-cccc-dddd",
        json={"originNm": "new_name.jpg"},
    )
    assert resp.status_code == 200
    assert resp.json()["originNm"] == "new_name.jpg"
    mock_rename.assert_called_once_with("aaaa-bbbb-cccc-dddd", "new_name.jpg")


@patch("app.api.endpoints.image_processing.rename_file")
async def test_rename_not_found(mock_rename, client: AsyncClient):
    """PATCH /api/image-processing/{id} — 존재하지 않는 파일"""
    mock_rename.side_effect = ValueError("file not found: unknown-id")
    resp = await client.patch(
        "/api/image-processing/unknown-id",
        json={"originNm": "new_name.jpg"},
    )
    assert resp.status_code == 404


async def test_rename_empty_name(client: AsyncClient):
    """PATCH /api/image-processing/{id} — 빈 파일명 유효성 검증"""
    resp = await client.patch(
        "/api/image-processing/aaaa-bbbb-cccc-dddd",
        json={"originNm": ""},
    )
    assert resp.status_code == 422
