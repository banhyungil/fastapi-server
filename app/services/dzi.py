"""DZI 타일 생성 + 이미지 다운로드."""

import time as _time
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from app.schemas.file import FilterType
from app.schemas.image_processing import PARAM_MODELS
from app.services.cache import CACHE_DIR
from app.services.operations import OPERATIONS

TILE_THRESHOLD = 4000  # px — 한 변이 이 이상이면 DZI 타일 생성


class DziResult:
    __slots__ = ("dzi_url", "image_url")

    def __init__(self, *, dzi_url: str | None = None, image_url: str | None = None) -> None:
        self.dzi_url = dzi_url
        self.image_url = image_url


def _process_chain_to_node(
    file_path: str,
    steps: list[dict[str, Any]],
    node_id: str,
) -> np.ndarray:
    """원본 이미지를 로드하고 steps 체인을 DFS로 처리하여 타겟 노드의 결과 이미지를 반환한다."""
    image = cv2.imread(file_path, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"failed to read image: {file_path}")

    children_map: dict[str | None, list[dict[str, Any]]] = {}
    for step in steps:
        parent_id = step.get("parentId")
        children_map.setdefault(parent_id, []).append(step)

    stack: list[tuple[dict[str, Any], np.ndarray]] = []
    roots = children_map.get(None, [])
    for step in reversed(roots):
        stack.append((step, image))

    while stack:
        step, parent_image = stack.pop()

        current_id: str = step["nodeId"]
        filter_type: FilterType = step["filterType"]
        parameters: dict[str, Any] = step.get("parameters", {})

        op = OPERATIONS.get(filter_type)
        if op is None:
            raise ValueError(f"unsupported filterType: {filter_type}")

        param_cls = PARAM_MODELS[filter_type]
        params = param_cls.model_validate(parameters)
        result_image = op(parent_image, params)

        if current_id == node_id:
            return result_image

        children = children_map.get(current_id, [])
        for child in reversed(children):
            stack.append((child, result_image))

    raise ValueError(f"target node not found in steps: {node_id}")


def _save_node_image(file_id: str, node_id: str, image: np.ndarray) -> str:
    """노드별 원본 크기 이미지를 파일로 저장하고 URL 경로를 반환한다."""
    dir_path = CACHE_DIR / file_id
    dir_path.mkdir(parents=True, exist_ok=True)

    file_path = dir_path / f"{node_id}.png"
    success, encoded = cv2.imencode(".png", image)
    if not success:
        raise RuntimeError("failed to encode cache image")
    file_path.write_bytes(encoded.tobytes())

    ts = int(_time.time())
    return f"/{str(file_path).replace(chr(92), '/')}?t={ts}"


def _ensure_libvips() -> None:
    """Windows 환경에서 libvips DLL 검색 경로를 등록한다 (최초 1회)."""
    import os
    import sys

    if sys.platform != "win32" or getattr(_ensure_libvips, "_done", False):
        return

    vips_bin = Path(os.environ.get("VIPS_HOME", "")) / "bin"
    if not vips_bin.exists():
        winget_base = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/WinGet/Packages"
        for d in winget_base.glob("libvips*"):
            candidate = next(d.glob("vips-dev-*/bin"), None)
            if candidate and candidate.exists():
                vips_bin = candidate
                break

    if vips_bin.exists():
        os.add_dll_directory(str(vips_bin))
        os.environ["PATH"] = str(vips_bin) + os.pathsep + os.environ.get("PATH", "")

    _ensure_libvips._done = True  # type: ignore[attr-defined]


def _save_node_dzi(file_id: str, node_id: str, image: np.ndarray) -> str:
    """고해상도 이미지를 DZI 타일로 변환하여 저장하고 .dzi URL을 반환한다."""
    _ensure_libvips()
    import pyvips

    dir_path = CACHE_DIR / file_id
    dir_path.mkdir(parents=True, exist_ok=True)

    if image.ndim == 2:
        vips_img = pyvips.Image.new_from_memory(
            image.tobytes(), image.shape[1], image.shape[0], 1, "uchar",
        )
    else:
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        vips_img = pyvips.Image.new_from_memory(
            rgb.tobytes(), image.shape[1], image.shape[0], image.shape[2], "uchar",
        )

    dzi_base = str(dir_path / node_id)
    tiles_dir = Path(f"{dzi_base}_files")
    if tiles_dir.exists():
        import shutil
        shutil.rmtree(tiles_dir, ignore_errors=True)

    vips_img.dzsave(dzi_base, tile_size=256, overlap=1, suffix=".jpg[Q=85]")  # type: ignore[attr-defined]

    ts = int(_time.time())
    dzi_path = f"{dzi_base}.dzi"
    return f"/{dzi_path.replace(chr(92), '/')}?t={ts}"


def generate_dzi_for_node(
    file_path: str,
    steps: list[dict[str, Any]],
    *,
    file_id: str,
    node_id: str,
) -> DziResult:
    """원본 이미지를 로드하고, steps 체인을 처리하여 타겟 노드의 DZI(또는 원본 이미지)를 생성한다."""
    if not steps:
        target_image = cv2.imread(file_path, cv2.IMREAD_COLOR)
        if target_image is None:
            raise ValueError(f"failed to read image: {file_path}")
    else:
        target_image = _process_chain_to_node(file_path, steps, node_id)

    h, w = target_image.shape[:2]
    if max(h, w) >= TILE_THRESHOLD:
        dzi_url = _save_node_dzi(file_id, node_id, target_image)
        return DziResult(dzi_url=dzi_url)
    else:
        image_url = _save_node_image(file_id, node_id, target_image)
        return DziResult(image_url=image_url)


def download_node_image(
    file_path: str,
    steps: list[dict[str, Any]],
    node_id: str,
) -> bytes:
    """원본 이미지에 steps 체인을 적용하고, 타겟 노드의 결과를 PNG 바이트로 반환한다."""
    target_image = _process_chain_to_node(file_path, steps, node_id)

    success, encoded = cv2.imencode(".png", target_image)
    if not success:
        raise RuntimeError("failed to encode image")
    return encoded.tobytes()
