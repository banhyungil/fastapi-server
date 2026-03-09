import pytest
import cv2
import numpy as np
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    """비동기 TestClient — 실제 서버 기동 없이 API 호출"""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.fixture
def test_image_bytes() -> bytes:
    """테스트용 100x100 PNG 이미지 바이트"""
    img = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
    _, encoded = cv2.imencode(".png", img)
    return encoded.tobytes()


@pytest.fixture
def test_large_image_bytes() -> bytes:
    """DZI 테스트용 5000x5000 PNG 이미지 바이트"""
    img = np.random.randint(0, 255, (5000, 5000, 3), dtype=np.uint8)
    _, encoded = cv2.imencode(".png", img)
    return encoded.tobytes()
