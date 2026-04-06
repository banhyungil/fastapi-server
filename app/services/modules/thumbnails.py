"""썸네일 생성/조회/삭제."""

import base64
from pathlib import Path

import cv2
import numpy as np

THUMBNAIL_DIR = Path("uploads/thumbnails")
THUMBNAIL_SIZE = 250
THUMBNAIL_SIZE_FILE = 150


def save_file_thumbnail(file_id: str, image_bytes: bytes, size: int = THUMBNAIL_SIZE_FILE) -> str:
    """업로드된 이미지 바이트로부터 썸네일을 생성하여 디스크에 저장하고, URL 경로를 반환한다."""
    THUMBNAIL_DIR.mkdir(parents=True, exist_ok=True)

    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if image is None:
        raise RuntimeError("failed to decode image for thumbnail")

    h, w = image.shape[:2]
    scale = size / max(h, w)
    if scale < 1.0:
        image = cv2.resize(image, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

    success, encoded = cv2.imencode(".webp", image, [cv2.IMWRITE_WEBP_QUALITY, 80])
    if not success:
        raise RuntimeError("failed to encode thumbnail")

    thumb_path = THUMBNAIL_DIR / f"{file_id}.webp"
    thumb_path.write_bytes(encoded.tobytes())
    return str(thumb_path).replace("\\", "/")


def get_file_thumbnail_url(file_id: str) -> str | None:
    """미리 생성된 썸네일 파일의 URL 경로를 반환한다. 없으면 None."""
    thumb_path = THUMBNAIL_DIR / f"{file_id}.webp"
    if thumb_path.exists():
        return str(thumb_path).replace("\\", "/")
    return None


def delete_file_thumbnail(file_id: str) -> None:
    """썸네일 파일을 삭제한다."""
    thumb_path = THUMBNAIL_DIR / f"{file_id}.webp"
    if thumb_path.exists():
        thumb_path.unlink()


def generate_thumbnail_base64(file_path: str, size: int = 200) -> str | None:
    """파일 경로로부터 썸네일 base64 data URL을 생성한다."""
    path = Path(file_path)
    if not path.exists():
        return None
    data = path.read_bytes()
    arr = np.frombuffer(data, dtype=np.uint8)
    image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if image is None:
        return None
    return encode_base64_thumbnail(image, thumbnail_size=size)


def encode_base64_thumbnail(image: np.ndarray, thumbnail_size: int | None = THUMBNAIL_SIZE) -> str:
    """WebP로 인코딩하여 data URL(base64)을 반환한다.
    thumbnail_size가 None이면 리사이즈 없이 무손실 인코딩."""
    if thumbnail_size is not None:
        h, w = image.shape[:2]
        scale = thumbnail_size / max(h, w)
        if scale < 1.0:
            image = cv2.resize(image, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
        # 썸네일: 손실 압축 (품질 80)
        success, encoded = cv2.imencode(".webp", image, [cv2.IMWRITE_WEBP_QUALITY, 80])
    else:
        # 풀해상도: 무손실 압축
        success, encoded = cv2.imencode(".webp", image, [cv2.IMWRITE_WEBP_QUALITY, 101])

    if not success:
        raise RuntimeError("failed to encode image")
    b64 = base64.b64encode(encoded.tobytes()).decode()
    return f"data:image/webp;base64,{b64}"
