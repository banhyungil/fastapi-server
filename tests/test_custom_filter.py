"""커스텀 필터 CRUD + 테스트 실행 API 테스트"""

import json
from unittest.mock import patch

from httpx import AsyncClient


SAMPLE_CODE = "result = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)"
SAMPLE_CODE_WITH_PARAMS = (
    "ksize = params.get('ksize', 3)\n"
    "gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)\n"
    "result = cv2.GaussianBlur(gray, (ksize, ksize), 0)"
)
SAMPLE_FILTER = {
    "id": "cf-test-uuid",
    "nm": "grayscale",
    "description": "그레이스케일 변환",
    "code": SAMPLE_CODE,
    "params": {},
    "version": 1,
    "created_at": "2026-03-11T00:00:00+00:00",
    "updated_at": "2026-03-11T00:00:00+00:00",
}


# ── CREATE ────────────────────────────────────────────────────────────────────


async def test_create_custom_filter(client: AsyncClient):
    """POST /api/custom-filters — 커스텀 필터 생성"""
    with patch(
        "app.api.endpoints.custom_filter.create_custom_filter",
        return_value=SAMPLE_FILTER,
    ):
        resp = await client.post(
            "/api/custom-filters",
            json={
                "nm": "grayscale",
                "description": "그레이스케일 변환",
                "code": SAMPLE_CODE,
                "params": {},
            },
        )
    assert resp.status_code == 201
    data = resp.json()
    assert data["id"] == "cf-test-uuid"
    assert data["nm"] == "grayscale"
    assert data["code"] == SAMPLE_CODE
    assert data["version"] == 1


# ── READ (목록) ──────────────────────────────────────────────────────────────


async def test_list_custom_filters(client: AsyncClient):
    """GET /api/custom-filters — 커스텀 필터 목록 조회"""
    with patch(
        "app.api.endpoints.custom_filter.list_custom_filters",
        return_value=[SAMPLE_FILTER],
    ):
        resp = await client.get("/api/custom-filters")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["nm"] == "grayscale"


async def test_list_custom_filters_empty(client: AsyncClient):
    """GET /api/custom-filters — 빈 목록"""
    with patch(
        "app.api.endpoints.custom_filter.list_custom_filters",
        return_value=[],
    ):
        resp = await client.get("/api/custom-filters")
    assert resp.status_code == 200
    assert resp.json()["items"] == []


# ── READ (상세) ──────────────────────────────────────────────────────────────


async def test_get_custom_filter_detail(client: AsyncClient):
    """GET /api/custom-filters/{id} — 커스텀 필터 상세 조회"""
    with patch(
        "app.api.endpoints.custom_filter.get_custom_filter",
        return_value=SAMPLE_FILTER,
    ):
        resp = await client.get("/api/custom-filters/cf-test-uuid")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == SAMPLE_CODE
    assert data["description"] == "그레이스케일 변환"


async def test_get_custom_filter_not_found(client: AsyncClient):
    """GET /api/custom-filters/{id} — 존재하지 않는 필터"""
    with patch(
        "app.api.endpoints.custom_filter.get_custom_filter",
        return_value=None,
    ):
        resp = await client.get("/api/custom-filters/nonexistent")
    assert resp.status_code == 404


# ── UPDATE ────────────────────────────────────────────────────────────────────


async def test_update_custom_filter(client: AsyncClient):
    """PUT /api/custom-filters/{id} — 커스텀 필터 수정"""
    updated = {**SAMPLE_FILTER, "nm": "gray-v2", "code": SAMPLE_CODE_WITH_PARAMS, "version": 2}
    with patch(
        "app.api.endpoints.custom_filter.modify_custom_filter",
        return_value=updated,
    ):
        resp = await client.put(
            "/api/custom-filters/cf-test-uuid",
            json={"nm": "gray-v2", "code": SAMPLE_CODE_WITH_PARAMS},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["nm"] == "gray-v2"
    assert data["version"] == 2


async def test_update_custom_filter_not_found(client: AsyncClient):
    """PUT /api/custom-filters/{id} — 존재하지 않는 필터 수정"""
    with patch(
        "app.api.endpoints.custom_filter.modify_custom_filter",
        return_value=None,
    ):
        resp = await client.put(
            "/api/custom-filters/nonexistent",
            json={"nm": "new-name"},
        )
    assert resp.status_code == 404


# ── DELETE ────────────────────────────────────────────────────────────────────


async def test_delete_custom_filter(client: AsyncClient):
    """DELETE /api/custom-filters/{id} — 커스텀 필터 삭제"""
    with patch(
        "app.api.endpoints.custom_filter.remove_custom_filter",
        return_value=True,
    ):
        resp = await client.delete("/api/custom-filters/cf-test-uuid")
    assert resp.status_code == 204


async def test_delete_custom_filter_not_found(client: AsyncClient):
    """DELETE /api/custom-filters/{id} — 존재하지 않는 필터 삭제"""
    with patch(
        "app.api.endpoints.custom_filter.remove_custom_filter",
        return_value=False,
    ):
        resp = await client.delete("/api/custom-filters/nonexistent")
    assert resp.status_code == 404


# ── TEST 실행 ────────────────────────────────────────────────────────────────


async def test_test_custom_filter(client: AsyncClient, test_image_bytes: bytes):
    """POST /api/custom-filters/{id}/test — 커스텀 필터 테스트 실행"""
    with patch(
        "app.api.endpoints.custom_filter.get_custom_filter",
        return_value=SAMPLE_FILTER,
    ):
        resp = await client.post(
            "/api/custom-filters/cf-test-uuid/test",
            data={"parameters": json.dumps({})},
            files={"image": ("test.png", test_image_bytes, "image/png")},
        )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"
    assert len(resp.content) > 0


async def test_test_custom_filter_with_params(client: AsyncClient, test_image_bytes: bytes):
    """POST /api/custom-filters/{id}/test — 파라미터 포함 테스트"""
    filter_with_params = {**SAMPLE_FILTER, "code": SAMPLE_CODE_WITH_PARAMS}
    with patch(
        "app.api.endpoints.custom_filter.get_custom_filter",
        return_value=filter_with_params,
    ):
        resp = await client.post(
            "/api/custom-filters/cf-test-uuid/test",
            data={"parameters": json.dumps({"ksize": 5})},
            files={"image": ("test.png", test_image_bytes, "image/png")},
        )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"


async def test_test_custom_filter_not_found(client: AsyncClient, test_image_bytes: bytes):
    """POST /api/custom-filters/{id}/test — 존재하지 않는 필터"""
    with patch(
        "app.api.endpoints.custom_filter.get_custom_filter",
        return_value=None,
    ):
        resp = await client.post(
            "/api/custom-filters/nonexistent/test",
            data={"parameters": "{}"},
            files={"image": ("test.png", test_image_bytes, "image/png")},
        )
    assert resp.status_code == 404


# ── 샌드박스 실행 엔진 단위 테스트 ──────────────────────────────────────────


async def test_execute_custom_filter_success():
    """execute_custom_filter — 정상 실행"""
    import numpy as np
    from app.services.custom_filter_service import execute_custom_filter

    image = np.zeros((100, 100, 3), dtype=np.uint8)
    code = "result = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)"
    result = execute_custom_filter(code, image, {})

    assert isinstance(result, np.ndarray)
    assert result.shape == (100, 100)


async def test_execute_custom_filter_with_params():
    """execute_custom_filter — params 사용"""
    import numpy as np
    from app.services.custom_filter_service import execute_custom_filter

    image = np.zeros((100, 100, 3), dtype=np.uint8)
    code = (
        "val = params.get('val', 128)\n"
        "result = np.full_like(image, val)"
    )
    result = execute_custom_filter(code, image, {"val": 200})

    assert isinstance(result, np.ndarray)
    assert result[0, 0, 0] == 200


async def test_execute_custom_filter_no_result():
    """execute_custom_filter — result 미할당 시 에러"""
    import numpy as np
    import pytest
    from app.services.custom_filter_service import execute_custom_filter

    image = np.zeros((100, 100, 3), dtype=np.uint8)
    code = "x = 1 + 1"

    with pytest.raises(ValueError, match="result"):
        execute_custom_filter(code, image, {})


async def test_execute_custom_filter_import_blocked():
    """execute_custom_filter — import 차단 확인"""
    import numpy as np
    import pytest
    from app.services.custom_filter_service import execute_custom_filter

    image = np.zeros((100, 100, 3), dtype=np.uint8)
    code = "import os\nresult = image"

    with pytest.raises(Exception):
        execute_custom_filter(code, image, {})


async def test_execute_custom_filter_preserves_original():
    """execute_custom_filter — 원본 이미지 보호 확인"""
    import numpy as np
    from app.services.custom_filter_service import execute_custom_filter

    image = np.full((10, 10, 3), 100, dtype=np.uint8)
    original = image.copy()
    code = "image[:] = 0\nresult = image"
    execute_custom_filter(code, image, {})

    assert np.array_equal(image, original)


async def test_execute_custom_filter_invalid_ndim():
    """execute_custom_filter — 1차원 배열 반환 시 에러"""
    import numpy as np
    import pytest
    from app.services.custom_filter_service import execute_custom_filter

    image = np.zeros((100, 100, 3), dtype=np.uint8)
    code = "result = np.array([1, 2, 3], dtype=np.uint8)"

    with pytest.raises(ValueError, match="ndim"):
        execute_custom_filter(code, image, {})


async def test_execute_custom_filter_invalid_channels():
    """execute_custom_filter — 유효하지 않은 채널 수 반환 시 에러"""
    import numpy as np
    import pytest
    from app.services.custom_filter_service import execute_custom_filter

    image = np.zeros((100, 100, 3), dtype=np.uint8)
    code = "result = np.zeros((100, 100, 2), dtype=np.uint8)"

    with pytest.raises(ValueError, match="채널"):
        execute_custom_filter(code, image, {})


async def test_execute_custom_filter_invalid_dtype():
    """execute_custom_filter — float64 반환 시 에러"""
    import numpy as np
    import pytest
    from app.services.custom_filter_service import execute_custom_filter

    image = np.zeros((100, 100, 3), dtype=np.uint8)
    code = "result = np.zeros((100, 100, 3), dtype=np.float64)"

    with pytest.raises(ValueError, match="uint8"):
        execute_custom_filter(code, image, {})
