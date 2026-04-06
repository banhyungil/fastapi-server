from httpx import AsyncClient
from pathlib import Path
from app.schemas.files_schema import FileListResponse
from app.services.modules.thumbnails import save_file_thumbnail
from typing import cast
import pytest
# opencv 파이썬 바인딩
import cv2

THUMBNAIL_DIR = Path("uploads/thumbnails")

async def test_create_humbnail(client: AsyncClient):
    # 파일 목록 조회
    res = await client.get("/api/files")
    # pydentic 모델 추출
    data = FileListResponse.model_validate(res.json())
    # 썸네일 이미지 가 있는지 검사
    for item in data.items:
        # 썸네일 파일 path에 파일 존재여부 확인
        thumb_path = THUMBNAIL_DIR / f"{item.id}.webp"
        if thumb_path.exists():
            continue
        
        item_path = Path(item.path)
        if not item_path.exists():
            raise FileNotFoundError
        
        item_image = item_path.read_bytes()

        save_file_thumbnail(str(item.id), item_image)


    # 없으면 썸네일 이미지 생성후 파일 저장


# 압축 원리
# # 원본: AAAAAABBBCC
# # 압축: A6B3C2        ← 같은 정보, 더 적은 바이트

# 손실 압축률 설정
# # 1: 최저 품질, 최소 용량
# # 100: 최고 품질, 최대 용량 (거의 무손실)
# #: 70 ~ 80: 적당한 품질, 용량 균형

# 리샘플링 vs 손실압축
# # 리샘플링: 픽셀수 자체를 줄임
# # 손실압축: 픽셀수 유지 하면서 용량 줄임

# 양자화는 정밀한 값을 거친 값으로 반올림하는 것입니다.

# 1. 기본 개념


# 원본:    3.7,  1.2,  0.3,  0.05
# 양자화:  4,    1,    0,    0       ← 작은 값은 0이 됨
# 2. JPEG에서의 실제 과정

# 8x8 픽셀 블록을 DCT(주파수 변환)하면 64개의 주파수 계수가 나옵니다.


# DCT 계수:        [320, 48, 15, 7, 3, 1]
# 양자화 테이블:    [16,  11, 10, 16, 24, 40]   ← 품질에 따라 달라짐

# 양자화 = DCT 계수 / 양자화 테이블 → 반올림

# 계산:            [320/16, 48/11, 15/10, 7/16, 3/24, 1/40]
#                = [20.0,   4.36,  1.5,   0.44, 0.125, 0.025]
# 반올림:          [20,     4,     2,     0,    0,     0]
# 뒤쪽(고주파 = 미세한 디테일)이 0이 되면서 저장할 데이터가 줄어듭니다. [20, 4, 2, 0, 0, 0]은 0이 많아서 압축이 잘 됩니다.

# 3. 역양자화 (디코딩)


# 양자화된 값:      [20,  4,   2,   0,  0,  0]
# × 양자화 테이블:  [16,  11,  10,  16, 24, 40]

# 복원:            [320, 44,  20,  0,  0,  0]
# 원본:            [320, 48,  15,  7,  3,  1]
# 48→44, 15→20처럼 근사치가 됩니다. 이게 손실이 발생하는 지점입니다.

# 4. quality와의 관계


# quality=90  → 양자화 테이블 값이 작음 → 나누는 수가 작아 정밀도 유지 → 고품질, 큰 용량
# quality=10  → 양자화 테이블 값이 큼  → 나누는 수가 커서 0이 많아짐  → 저품질, 작은 용량
# 정리하면: 나눗셈 → 반올림 → 정보 손실 → 0이 많아짐 → 압축 효율 상승


# 양자화
# 이미지영

arr = list(range(1, 11))
print(str(num) for num in arr)

arr2 = (num * 2 for num in arr)
arr3 = (num for num in arr if num % 2 == 0)

arr3 = [1,2,3] + [4,5,6]
