from httpx import AsyncClient

# 해당 파일만 실행
# # pytest tests/integration/test_image_gallery.py -v

# 특정 테스트 함수만 실행
# # pytest tests/integration/test_image_gallery.py::test_get_saved_images -v

# 출력(print) 보려면 -s 추가
# # pytest tests/integration/test_image_gallery.py -v -s

# 현재 파일 디버깅 테스트
# # 디버깅 패널에서 설정
# # RUN AND DEBUG를 Current File로 설정


async def test_get_saved_images(client: AsyncClient): 
    res = await client.get('/api/files')
    assert res.status_code == 200

    data = res.json()
    print(f"items: {data["items"]}")
    