"""DZI 타일 생성 서비스 단위 테스트"""

import shutil

import numpy as np

from app.services.cache import CACHE_DIR
from app.services.dzi import TILE_THRESHOLD, _save_node_dzi, _save_node_image
from app.services.files_service import process_image_batch_tree


def test_save_node_dzi_creates_tiles():
    """_save_node_dzi — DZI 파일 및 타일 디렉토리 생성 확인"""
    img = np.random.randint(0, 255, (5000, 5000, 3), dtype=np.uint8)
    url = _save_node_dzi("test-dzi-fid", "test-nid", img)

    assert url.startswith("/uploads/cache/test-dzi-fid/test-nid.dzi")
    assert "?t=" in url
    assert (CACHE_DIR / "test-dzi-fid" / "test-nid.dzi").exists()
    assert (CACHE_DIR / "test-dzi-fid" / "test-nid_files").is_dir()

    # 타일 레벨 디렉토리가 존재하는지 확인
    tiles_dir = CACHE_DIR / "test-dzi-fid" / "test-nid_files"
    levels = [d for d in tiles_dir.iterdir() if d.is_dir()]
    assert len(levels) > 0

    shutil.rmtree(CACHE_DIR / "test-dzi-fid", ignore_errors=True)


def test_save_node_dzi_grayscale():
    """_save_node_dzi — grayscale 이미지도 처리 가능"""
    img = np.random.randint(0, 255, (5000, 5000), dtype=np.uint8)
    url = _save_node_dzi("test-dzi-gray", "gray-nid", img)

    assert (CACHE_DIR / "test-dzi-gray" / "gray-nid.dzi").exists()
    shutil.rmtree(CACHE_DIR / "test-dzi-gray", ignore_errors=True)


def test_save_node_dzi_overwrites_existing():
    """_save_node_dzi — 동일 node_id로 재호출 시 기존 타일 덮어쓰기"""
    img = np.random.randint(0, 255, (5000, 5000, 3), dtype=np.uint8)
    _save_node_dzi("test-dzi-overwrite", "nid", img)

    # 다른 이미지로 재호출
    img2 = np.zeros((5000, 5000, 3), dtype=np.uint8)
    url2 = _save_node_dzi("test-dzi-overwrite", "nid", img2)

    assert (CACHE_DIR / "test-dzi-overwrite" / "nid.dzi").exists()
    assert url2.startswith("/uploads/cache/test-dzi-overwrite/nid.dzi")

    shutil.rmtree(CACHE_DIR / "test-dzi-overwrite", ignore_errors=True)


def test_save_node_image_thumbnail():
    """_save_node_image — 썸네일 크기로 저장"""
    img = np.random.randint(0, 255, (1000, 1000, 3), dtype=np.uint8)
    url = _save_node_image("test-thumb", "nid", img, full_size=False)

    assert url.startswith("/uploads/cache/test-thumb/nid.png")
    shutil.rmtree(CACHE_DIR / "test-thumb", ignore_errors=True)


def test_save_node_image_full_size():
    """_save_node_image — 원본 크기로 저장"""
    img = np.random.randint(0, 255, (500, 500, 3), dtype=np.uint8)
    url = _save_node_image("test-full", "nid", img, full_size=True)

    assert url.startswith("/uploads/cache/test-full/nid.png")
    shutil.rmtree(CACHE_DIR / "test-full", ignore_errors=True)


def test_batch_tree_no_dzi_for_small_image(test_image_bytes: bytes):
    """process_image_batch_tree — 저해상도 이미지는 DZI 생성 안 됨"""
    import cv2

    steps = [
        {"nodeId": "n1", "filterType": "blur", "parameters": {"kernelSize": 3}, "parentId": None},
    ]
    result = process_image_batch_tree(
        image_bytes=test_image_bytes,
        steps=steps,
        file_id="test-no-dzi",
    )
    assert len(result.node_results) == 1
    assert result.node_results[0].dzi_url is None

    shutil.rmtree(CACHE_DIR / "test-no-dzi", ignore_errors=True)


def test_tile_threshold_value():
    """TILE_THRESHOLD 상수 확인"""
    assert TILE_THRESHOLD == 4000
