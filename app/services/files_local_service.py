"""로컬 디렉토리 스캔 + 파일 등록 서비스."""

import logging
import mimetypes
import os
from pathlib import Path

import cv2
import numpy as np

from app.repos.files_repo import (
    FileRow,
    InsertedFileMeta,
    find_local_by_path,
    insert_file_row,
)
from app.services.thumbnails import save_file_thumbnail, encode_base64_thumbnail

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
SUPPORTED_MIMES = {"image/png", "image/jpeg", "image/webp", "image/bmp", "image/tiff"}


def _get_mime_type(path: str) -> str | None:
    """파일 경로에서 MIME 타입을 추측하여 반환한다."""
    mime, _ = mimetypes.guess_type(path)
    return mime


SCAN_THUMBNAIL_SIZE = 120


def _read_image(path: str) -> np.ndarray | None:
    """이미지 파일을 읽어 ndarray로 반환한다. 실패 시 None."""
    return cv2.imread(path, cv2.IMREAD_COLOR)


def _normalize_path(path: str) -> str:
    """절대 경로로 변환하여 반환 (Windows 경로 구분자 통일)"""
    return str(Path(path).resolve()).replace("\\", "/")


def scan_directory(
    dir_path: str,
    *,
    recursive: bool = False,
    use_thumbnail: bool = True,
) -> list[dict[str, object]]:
    """디렉토리를 스캔하여 지원되는 이미지 파일 목록을 반환한다."""
    root = Path(dir_path)
    if not root.is_dir():
        raise ValueError(f"디렉토리가 존재하지 않습니다: {dir_path}")

    results: list[dict[str, object]] = []

    entries = root.rglob("*") if recursive else root.iterdir()
    for entry in entries:
        if not entry.is_file():
            continue
        # 이미지 확장자가 아닌 경우 제외
        if entry.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue

        abs_path = _normalize_path(str(entry))
        mime = _get_mime_type(abs_path)
        if mime not in SUPPORTED_MIMES:
            continue

        size_bytes = entry.stat().st_size

        img = _read_image(abs_path)
        if img is None:
            continue
        h, w = img.shape[:2]

        thumbnail_url = ""
        if use_thumbnail:
            try:
                thumbnail_url = encode_base64_thumbnail(img, SCAN_THUMBNAIL_SIZE)
            except Exception:
                pass

        existing = find_local_by_path(abs_path)

        results.append({
            "path": abs_path,
            "file_name": entry.name,
            "mime_type": mime,
            "size_bytes": size_bytes,
            "width": w,
            "height": h,
            "thumbnail_url": thumbnail_url,
            "already_registered": existing is not None,
        })

    return results


def register_local_files(
    paths: list[str],
) -> list[dict[str, object]]:
    """로컬 파일 경로 목록을 t_file에 등록한다."""
    results: list[dict[str, object]] = []

    for raw_path in paths:
        abs_path = _normalize_path(raw_path)
        file_path = Path(abs_path)

        if not file_path.is_file():
            logger.warning("파일이 존재하지 않습니다: %s", abs_path)
            continue

        mime = _get_mime_type(abs_path)
        if mime not in SUPPORTED_MIMES:
            logger.warning("지원하지 않는 MIME 타입: %s (%s)", mime, abs_path)
            continue

        # 이미 등록된 경로는 기존 레코드 반환
        existing = find_local_by_path(abs_path)
        if existing is not None:
            results.append({
                "id": existing["id"],
                "origin_nm": existing["origin_nm"],
                "nm": existing["nm"],
                "path": existing["path"],
                "mime_type": existing["mime_type"],
                "size_bytes": existing["size_bytes"],
                "uploaded_at": existing["uploaded_at"],
                "source_type": existing["source_type"],
                "width": existing.get("width"),
                "height": existing.get("height"),
            })
            continue

        size_bytes = file_path.stat().st_size
        img = _read_image(abs_path)
        if img is None:
            logger.warning("이미지 디코딩 실패: %s", abs_path)
            continue
        h, w = img.shape[:2]
        width, height = w, h

        inserted: InsertedFileMeta = insert_file_row(
            origin_nm=file_path.name,
            nm=file_path.name,
            path=abs_path,
            mime_type=mime,
            size_bytes=size_bytes,
            options={},
            source_type="local",
            width=width,
            height=height,
        )

        # 썸네일 생성
        try:
            image_bytes = file_path.read_bytes()
            save_file_thumbnail(str(inserted["id"]), image_bytes)
        except Exception:
            logger.warning("썸네일 생성 실패: %s", abs_path)

        results.append({
            "id": inserted["id"],
            "origin_nm": file_path.name,
            "nm": file_path.name,
            "path": abs_path,
            "mime_type": mime,
            "size_bytes": size_bytes,
            "uploaded_at": inserted["uploaded_at"],
            "source_type": "local",
            "width": width,
            "height": height,
        })

    return results
