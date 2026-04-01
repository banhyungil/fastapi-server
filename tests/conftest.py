import pytest
import cv2
import numpy as np
from httpx import ASGITransport, AsyncClient
import logging

from app.main import app
from app.core.database import pool

# psycopg(사이코피지) 디버깅을 위해 로깅 레벨 DEBUG 설정
logging.basicConfig(level=logging.DEBUG)

# scope="session": 테스트 세션 전체에서 하나의 DB 풀을 공유한다. (테스트 함수마다 새로 생성하지 않음)
# autouse=True: 모든 테스트에서 자동으로 이 fixture가 적용된다. 
@pytest.fixture(scope="session", autouse=True)
def db_pool():
    pool.open()
    yield
    pool.close()

# conftest.py 기능
# # 같은 디렉터리 하위 파일에서 정의된 fixture 사용가능
# # test 함수 인자명을 통해 매칭됨.

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
