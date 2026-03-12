from collections.abc import Callable
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from app.schemas.file import PrcType

# ── 캐시 설정 ─────────────────────────────────────────────────────────────────

CACHE_DIR = Path("uploads/cache")
CACHE_TTL_SECONDS = 60 * 60       # 1시간 (file_id 디렉토리 단위)
CACHE_MAX_BYTES = 1024 * 1024 * 1024  # 1GB (전체 cache 폴더)
TILE_THRESHOLD = 4000             # px — 한 변이 이 이상이면 DZI 타일 생성
THUMBNAIL_SIZE = 150              # px — 썸네일 기본 해상도
from app.schemas.image_processing import (
    PARAM_MODELS,
    AdaptiveThresholdParams,
    BilateralFilterParams,
    BoxFilterParams,
    BrightnessParams,
    CannyParams,
    ContourParams,
    CustomFilterParams,
    GammaParams,
    GaussianBlurParams,
    KernelParams,
    LaplacianParams,
    MorphologicalParams,
    NoParams,
    SobelParams,
    ThresholdParams,
)


# ── 상수 ──────────────────────────────────────────────────────────────────────

THRESHOLD_TYPE_MAP: dict[str, int] = {
    "binary": cv2.THRESH_BINARY,
    "inverse": cv2.THRESH_BINARY_INV,
    "tozero": cv2.THRESH_TOZERO,
    "tozeroInverse": cv2.THRESH_TOZERO_INV,
    "truncate": cv2.THRESH_TRUNC,
}

MORPH_SHAPE_MAP: dict[str, int] = {
    "rect": cv2.MORPH_RECT,
    "ellipse": cv2.MORPH_ELLIPSE,
    "cross": cv2.MORPH_CROSS,
}

ADAPTIVE_METHOD_MAP: dict[str, int] = {
    "gaussian": cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
    "mean": cv2.ADAPTIVE_THRESH_MEAN_C,
}


# ── 헬퍼 ──────────────────────────────────────────────────────────────────────

def _to_gray(image: np.ndarray) -> np.ndarray:
    if image.ndim == 2 or (image.ndim == 3 and image.shape[2] == 1):
        return image if image.ndim == 2 else image[:, :, 0]
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def _ensure_odd(k: int) -> int:
    k = max(1, k)
    return k if k % 2 == 1 else k + 1


def _morph_kernel(params: MorphologicalParams) -> np.ndarray:
    shape = MORPH_SHAPE_MAP.get(params.kernel_shape, cv2.MORPH_RECT)
    k = _ensure_odd(params.kernel_size)
    return cv2.getStructuringElement(shape, (k, k))


# ── Edge Detection ────────────────────────────────────────────────────────────

def _op_sobel(image: np.ndarray, params: SobelParams) -> np.ndarray:
    k = _ensure_odd(min(params.kernel_size, 7))
    gray = _to_gray(image)
    grad_x = cv2.Sobel(gray, cv2.CV_64F, params.dx, params.dy, ksize=k, scale=params.scale)
    grad_y = cv2.Sobel(gray, cv2.CV_64F, params.dy, params.dx, ksize=k, scale=params.scale)
    magnitude = cv2.magnitude(grad_x, grad_y)
    return cv2.convertScaleAbs(magnitude)


def _op_prewitt(image: np.ndarray, _params: NoParams) -> np.ndarray:
    gray = _to_gray(image)
    kernel_x = np.array([[1, 0, -1], [1, 0, -1], [1, 0, -1]], dtype=np.float32)
    kernel_y = np.array([[1, 1, 1], [0, 0, 0], [-1, -1, -1]], dtype=np.float32)
    prewitt_x = cv2.filter2D(gray, cv2.CV_32F, kernel_x)
    prewitt_y = cv2.filter2D(gray, cv2.CV_32F, kernel_y)
    magnitude = cv2.magnitude(prewitt_x, prewitt_y)
    return cv2.convertScaleAbs(magnitude)


def _op_laplacian(image: np.ndarray, params: LaplacianParams) -> np.ndarray:
    k = _ensure_odd(params.kernel_size)
    gray = _to_gray(image)
    laplacian = cv2.Laplacian(gray, cv2.CV_64F, ksize=k, scale=params.scale, delta=params.delta)
    return cv2.convertScaleAbs(laplacian)


def _op_canny(image: np.ndarray, params: CannyParams) -> np.ndarray:
    gray = _to_gray(image)
    aperture = _ensure_odd(min(params.aperture_size, 7))
    return cv2.Canny(gray, params.threshold1, params.threshold2, apertureSize=aperture)


def _op_roberts(image: np.ndarray, _params: NoParams) -> np.ndarray:
    gray = _to_gray(image)
    kernel_x = np.array([[1, 0], [0, -1]], dtype=np.float32)
    kernel_y = np.array([[0, 1], [-1, 0]], dtype=np.float32)
    roberts_x = cv2.filter2D(gray, cv2.CV_32F, kernel_x)
    roberts_y = cv2.filter2D(gray, cv2.CV_32F, kernel_y)
    magnitude = cv2.magnitude(roberts_x, roberts_y)
    return cv2.convertScaleAbs(magnitude)


# ── Blurring ──────────────────────────────────────────────────────────────────

def _op_gaussian(image: np.ndarray, params: GaussianBlurParams) -> np.ndarray:
    k = _ensure_odd(params.kernel_size)
    return cv2.GaussianBlur(image, (k, k), params.sigma_x)


def _op_blur(image: np.ndarray, params: KernelParams) -> np.ndarray:
    k = max(1, params.kernel_size)
    return cv2.blur(image, (k, k))


def _op_gaussian_blur(image: np.ndarray, params: GaussianBlurParams) -> np.ndarray:
    k = _ensure_odd(params.kernel_size)
    return cv2.GaussianBlur(image, (k, k), params.sigma_x)


def _op_median_blur(image: np.ndarray, params: KernelParams) -> np.ndarray:
    k = _ensure_odd(params.kernel_size)
    return cv2.medianBlur(image, k)


def _op_bilateral_filter(image: np.ndarray, params: BilateralFilterParams) -> np.ndarray:
    return cv2.bilateralFilter(image, d=params.d, sigmaColor=params.sigma_color, sigmaSpace=params.sigma_space)


def _op_box_filter(image: np.ndarray, params: BoxFilterParams) -> np.ndarray:
    k = max(1, params.kernel_size)
    return cv2.boxFilter(image, -1, (k, k))


# ── Contour Detection ────────────────────────────────────────────────────────

def _op_find_contour(image: np.ndarray, params: ContourParams) -> np.ndarray:
    gray = _to_gray(image)
    _, binary = cv2.threshold(gray, params.threshold_value, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    result = image.copy()
    cv2.drawContours(result, contours, -1, tuple(params.color), params.thickness)
    return result


def _op_convex_hull(image: np.ndarray, params: ContourParams) -> np.ndarray:
    gray = _to_gray(image)
    _, binary = cv2.threshold(gray, params.threshold_value, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    result = image.copy()
    hulls = [cv2.convexHull(c) for c in contours]
    cv2.drawContours(result, hulls, -1, tuple(params.color), params.thickness)
    return result


def _op_bounding_box(image: np.ndarray, params: ContourParams) -> np.ndarray:
    gray = _to_gray(image)
    _, binary = cv2.threshold(gray, params.threshold_value, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    result = image.copy()
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        cv2.rectangle(result, (x, y), (x + w, y + h), tuple(params.color), params.thickness)
    return result


# ── Brightness ────────────────────────────────────────────────────────────────

def _op_brightness_plus(image: np.ndarray, params: BrightnessParams) -> np.ndarray:
    return cv2.convertScaleAbs(image, alpha=params.alpha, beta=abs(params.beta))


def _op_brightness_minus(image: np.ndarray, params: BrightnessParams) -> np.ndarray:
    return cv2.convertScaleAbs(image, alpha=params.alpha, beta=-abs(params.beta))


def _op_gamma(image: np.ndarray, params: GammaParams) -> np.ndarray:
    inv_gamma = 1.0 / params.gamma
    table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in range(256)]).astype("uint8")
    return cv2.LUT(image, table)


def _op_histogram_equalization(image: np.ndarray, _params: NoParams) -> np.ndarray:
    gray = _to_gray(image)
    return cv2.equalizeHist(gray)


# ── Thresholding ──────────────────────────────────────────────────────────────

def _op_threshold(image: np.ndarray, params: ThresholdParams, threshold_type: int) -> np.ndarray:
    gray = _to_gray(image)
    _, result = cv2.threshold(gray, params.threshold_value, params.max_value, threshold_type)
    return result


def _op_threshold_binary(image: np.ndarray, params: ThresholdParams) -> np.ndarray:
    return _op_threshold(image, params, THRESHOLD_TYPE_MAP["binary"])


def _op_threshold_inverse(image: np.ndarray, params: ThresholdParams) -> np.ndarray:
    return _op_threshold(image, params, THRESHOLD_TYPE_MAP["inverse"])


def _op_threshold_tozero(image: np.ndarray, params: ThresholdParams) -> np.ndarray:
    return _op_threshold(image, params, THRESHOLD_TYPE_MAP["tozero"])


def _op_threshold_tozero_inverse(image: np.ndarray, params: ThresholdParams) -> np.ndarray:
    return _op_threshold(image, params, THRESHOLD_TYPE_MAP["tozeroInverse"])


def _op_threshold_truncate(image: np.ndarray, params: ThresholdParams) -> np.ndarray:
    return _op_threshold(image, params, THRESHOLD_TYPE_MAP["truncate"])


def _op_threshold_otsu(image: np.ndarray, params: ThresholdParams) -> np.ndarray:
    gray = _to_gray(image)
    _, result = cv2.threshold(gray, 0, params.max_value, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    return result


def _op_adaptive_threshold(image: np.ndarray, params: AdaptiveThresholdParams) -> np.ndarray:
    gray = _to_gray(image)
    method = ADAPTIVE_METHOD_MAP.get(params.adaptive_method, cv2.ADAPTIVE_THRESH_GAUSSIAN_C)
    block = _ensure_odd(max(3, params.block_size))
    return cv2.adaptiveThreshold(gray, params.max_value, method, cv2.THRESH_BINARY, block, params.c)


# ── Morphological ─────────────────────────────────────────────────────────────

def _op_erosion(image: np.ndarray, params: MorphologicalParams) -> np.ndarray:
    kernel = _morph_kernel(params)
    return cv2.erode(image, kernel, iterations=params.iterations)


def _op_dilation(image: np.ndarray, params: MorphologicalParams) -> np.ndarray:
    kernel = _morph_kernel(params)
    return cv2.dilate(image, kernel, iterations=params.iterations)


def _op_opening(image: np.ndarray, params: MorphologicalParams) -> np.ndarray:
    kernel = _morph_kernel(params)
    return cv2.morphologyEx(image, cv2.MORPH_OPEN, kernel, iterations=params.iterations)


def _op_closing(image: np.ndarray, params: MorphologicalParams) -> np.ndarray:
    kernel = _morph_kernel(params)
    return cv2.morphologyEx(image, cv2.MORPH_CLOSE, kernel, iterations=params.iterations)


# ── Custom ────────────────────────────────────────────────────────────────────

def _op_custom(image: np.ndarray, params: CustomFilterParams) -> np.ndarray:
    from app.core.errors import AppError, ErrorCode
    from app.repos.custom_filter_repo import get_custom_filter_by_id
    from app.services.custom_filter_service import execute_custom_filter

    filter_data = get_custom_filter_by_id(params.filter_id)
    if not filter_data:
        raise AppError(
            code=ErrorCode.CUSTOM_FILTER_NOT_FOUND,
            message=f"커스텀 필터를 찾을 수 없습니다: {params.filter_id}",
            status_code=404,
            detail={"filter_id": params.filter_id},
        )
    return execute_custom_filter(filter_data["code"], image, params.parameters)


# ── OPERATIONS 매핑 ───────────────────────────────────────────────────────────

ImageOperation = Callable[..., np.ndarray]

OPERATIONS: dict[PrcType, ImageOperation] = {
    # Edge Detection
    "sobel": _op_sobel,
    "prewitt": _op_prewitt,
    "laplacian": _op_laplacian,
    "canny": _op_canny,
    "roberts": _op_roberts,
    # Blurring
    "gaussian": _op_gaussian,
    "blur": _op_blur,
    "gaussianBlur": _op_gaussian_blur,
    "medianBlur": _op_median_blur,
    "bilateralFilter": _op_bilateral_filter,
    "boxFilter": _op_box_filter,
    # Contour Detection
    "findContour": _op_find_contour,
    "convexHull": _op_convex_hull,
    "boundingBox": _op_bounding_box,
    # Brightness
    "plus": _op_brightness_plus,
    "minus": _op_brightness_minus,
    "gamma": _op_gamma,
    "histogramEqualization": _op_histogram_equalization,
    # Thresholding
    "binary": _op_threshold_binary,
    "inverse": _op_threshold_inverse,
    "tozero": _op_threshold_tozero,
    "tozeroInverse": _op_threshold_tozero_inverse,
    "truncate": _op_threshold_truncate,
    "otsu": _op_threshold_otsu,
    "adaptive": _op_adaptive_threshold,
    # Morphological
    "erosion": _op_erosion,
    "dilation": _op_dilation,
    "opening": _op_opening,
    "closing": _op_closing,
    # Custom
    "custom": _op_custom,
}


# ── 메인 처리 함수 ────────────────────────────────────────────────────────────

def process_image(
    prc_type: PrcType,
    image_bytes: bytes,
    parameters: dict[str, Any] | None = None,
) -> bytes:
    if not image_bytes:
        raise ValueError("empty image payload")

    image_array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("invalid image payload")

    op = OPERATIONS.get(prc_type)
    if op is None:
        raise ValueError(f"unsupported prcType: {prc_type}")

    param_cls = PARAM_MODELS[prc_type]
    params = param_cls.model_validate(parameters or {})
    processed = op(image, params)

    success, encoded = cv2.imencode(".png", processed)
    if not success:
        raise RuntimeError("failed to encode processed image")

    return encoded.tobytes()


class StepResult:
    __slots__ = ("prc_type", "execution_ms")

    def __init__(self, prc_type: str, execution_ms: float) -> None:
        self.prc_type = prc_type
        self.execution_ms = execution_ms


class BatchResult:
    __slots__ = ("image_bytes", "steps", "total_execution_ms")

    def __init__(self, image_bytes: bytes, steps: list[StepResult], total_execution_ms: float) -> None:
        self.image_bytes = image_bytes
        self.steps = steps
        self.total_execution_ms = total_execution_ms


def process_image_batch(
    image_bytes: bytes,
    steps: list[dict[str, Any]],
) -> BatchResult:
    """노드리스트 순서대로 이미지를 연쇄 처리한다."""
    import time

    if not image_bytes:
        raise ValueError("empty image payload")

    image_array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("invalid image payload")

    step_results: list[StepResult] = []
    total_start = time.perf_counter()

    for step in steps:
        prc_type: PrcType = step["prcType"]
        parameters: dict[str, Any] = step.get("parameters", {})

        op = OPERATIONS.get(prc_type)
        if op is None:
            raise ValueError(f"unsupported prcType: {prc_type}")

        param_cls = PARAM_MODELS[prc_type]
        params = param_cls.model_validate(parameters)

        step_start = time.perf_counter()
        image = op(image, params)
        step_ms = (time.perf_counter() - step_start) * 1000

        step_results.append(StepResult(prc_type=prc_type, execution_ms=round(step_ms, 2)))

    total_ms = (time.perf_counter() - total_start) * 1000

    success, encoded = cv2.imencode(".png", image)
    if not success:
        raise RuntimeError("failed to encode processed image")

    return BatchResult(
        image_bytes=encoded.tobytes(),
        steps=step_results,
        total_execution_ms=round(total_ms, 2),
    )


# ── 캐시 유틸 ──────────────────────────────────────────────────────────────────

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
    return _encode_thumbnail(image, thumbnail_size=size)


def _encode_thumbnail(image: np.ndarray, thumbnail_size: int = THUMBNAIL_SIZE) -> str:
    """썸네일을 WebP로 인코딩하여 data URL(base64)을 반환한다."""
    import base64

    h, w = image.shape[:2]
    scale = thumbnail_size / max(h, w)
    if scale < 1.0:
        image = cv2.resize(image, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

    success, encoded = cv2.imencode(".webp", image, [cv2.IMWRITE_WEBP_QUALITY, 80])
    if not success:
        raise RuntimeError("failed to encode thumbnail")
    b64 = base64.b64encode(encoded.tobytes()).decode()
    return f"data:image/webp;base64,{b64}"


def _save_node_image(file_id: str, node_id: str, image: np.ndarray) -> str:
    """노드별 원본 크기 이미지를 파일로 저장하고 URL 경로를 반환한다."""
    import time as _time

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
        # winget 기본 설치 경로 탐색
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
    import time as _time

    _ensure_libvips()
    import pyvips

    dir_path = CACHE_DIR / file_id
    dir_path.mkdir(parents=True, exist_ok=True)

    # OpenCV BGR → RGB 변환 후 pyvips 이미지 생성
    if image.ndim == 2:
        # grayscale
        vips_img = pyvips.Image.new_from_memory(
            image.tobytes(), image.shape[1], image.shape[0], 1, "uchar",
        )
    else:
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        vips_img = pyvips.Image.new_from_memory(
            rgb.tobytes(), image.shape[1], image.shape[0], image.shape[2], "uchar",
        )

    dzi_base = str(dir_path / node_id)
    # 기존 타일 디렉토리 제거 후 재생성
    tiles_dir = Path(f"{dzi_base}_files")
    if tiles_dir.exists():
        import shutil
        shutil.rmtree(tiles_dir, ignore_errors=True)

    vips_img.dzsave(dzi_base, tile_size=256, overlap=1, suffix=".jpg[Q=85]")  # type: ignore[attr-defined]

    ts = int(_time.time())
    dzi_path = f"{dzi_base}.dzi"
    return f"/{dzi_path.replace(chr(92), '/')}?t={ts}"


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

    # parentId → children 맵 구축
    children_map: dict[str | None, list[dict[str, Any]]] = {}
    for step in steps:
        parent_id = step.get("parentId")
        children_map.setdefault(parent_id, []).append(step)

    # DFS로 타겟 노드까지의 체인만 처리
    stack: list[tuple[dict[str, Any], np.ndarray]] = []

    roots = children_map.get(None, [])
    for step in reversed(roots):
        stack.append((step, image))

    while stack:
        step, parent_image = stack.pop()

        current_id: str = step["nodeId"]
        prc_type: PrcType = step["prcType"]
        parameters: dict[str, Any] = step.get("parameters", {})

        op = OPERATIONS.get(prc_type)
        if op is None:
            raise ValueError(f"unsupported prcType: {prc_type}")

        param_cls = PARAM_MODELS[prc_type]
        params = param_cls.model_validate(parameters)
        result_image = op(parent_image, params)

        if current_id == node_id:
            return result_image

        # 자식 노드들을 스택에 추가
        children = children_map.get(current_id, [])
        for child in reversed(children):
            stack.append((child, result_image))

    raise ValueError(f"target node not found in steps: {node_id}")


def generate_dzi_for_node(
    file_path: str,
    steps: list[dict[str, Any]],
    *,
    file_id: str,
    node_id: str,
) -> DziResult:
    """원본 이미지를 로드하고, steps 체인을 처리하여 타겟 노드의 DZI(또는 원본 이미지)를 생성한다.

    고해상도(>= TILE_THRESHOLD)이면 DZI 타일 생성, 저해상도이면 원본 PNG 저장.
    """
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


def cleanup_cache() -> None:
    """file_id 디렉토리 단위 TTL 삭제 + 전체 폴더 크기 제한."""
    import shutil
    import time as _time

    if not CACHE_DIR.exists():
        return

    now = _time.time()
    dirs = [d for d in CACHE_DIR.iterdir() if d.is_dir()]

    # 1) TTL 기반 삭제 — 디렉토리 mtime이 TTL 초과하면 통째로 삭제
    remaining: list[Path] = []
    for d in dirs:
        if now - d.stat().st_mtime > CACHE_TTL_SECONDS:
            shutil.rmtree(d, ignore_errors=True)
        else:
            remaining.append(d)

    # 2) 전체 폴더 크기 제한 (LRU — 가장 오래된 디렉토리부터 삭제)
    def _dir_size(d: Path) -> int:
        return sum(f.stat().st_size for f in d.rglob("*") if f.is_file())

    remaining.sort(key=lambda d: d.stat().st_mtime)
    total = sum(_dir_size(d) for d in remaining)
    while total > CACHE_MAX_BYTES and remaining:
        old = remaining.pop(0)
        total -= _dir_size(old)
        shutil.rmtree(old, ignore_errors=True)


# ── 트리 배치 처리 ───────────────────────────────────────────────────────────

class TreeNodeResult:
    __slots__ = ("node_id", "image_url", "execution_ms")

    def __init__(self, node_id: str, image_url: str, execution_ms: float) -> None:
        self.node_id = node_id
        self.image_url = image_url
        self.execution_ms = execution_ms


class TreeBatchResult:
    __slots__ = ("node_results", "total_execution_ms")

    def __init__(self, node_results: list[TreeNodeResult], total_execution_ms: float) -> None:
        self.node_results = node_results
        self.total_execution_ms = total_execution_ms


def process_image_batch_tree(
    image_bytes: bytes,
    steps: list[dict[str, Any]],
    *,
    thumbnail_size: int | None = None,
) -> TreeBatchResult:
    """트리 구조의 steps를 DFS로 순회하며 이미지를 처리한다.

    각 step은 { nodeId, prcType, parameters, parentId } 형태.
    parentId가 null이면 루트 노드(입력 이미지를 직접 받음).
    같은 parentId를 가진 siblings는 동일 입력에 서로 다른 알고리즘을 적용(분기).
    결과는 썸네일(base64 data URL)로 반환한다 (디스크 I/O 없음).
    """
    import time

    if not image_bytes:
        raise ValueError("empty image payload")

    image_array = np.frombuffer(image_bytes, dtype=np.uint8)
    root_image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    if root_image is None:
        raise ValueError("invalid image payload")

    # parentId → children 맵 구축
    children_map: dict[str | None, list[dict[str, Any]]] = {}
    for step in steps:
        parent_id = step.get("parentId")
        children_map.setdefault(parent_id, []).append(step)

    node_images: dict[str, np.ndarray] = {}
    node_results: list[TreeNodeResult] = []

    total_start = time.perf_counter()

    # DFS 순회 (스택 기반) — (step, parent_image)
    stack: list[tuple[dict[str, Any], np.ndarray]] = []

    roots = children_map.get(None, [])
    for step in reversed(roots):
        stack.append((step, root_image))

    while stack:
        step, parent_image = stack.pop()

        node_id: str = step["nodeId"]
        prc_type: PrcType = step["prcType"]
        parameters: dict[str, Any] = step.get("parameters", {})

        op = OPERATIONS.get(prc_type)
        if op is None:
            raise ValueError(f"unsupported prcType: {prc_type}")

        param_cls = PARAM_MODELS[prc_type]
        params = param_cls.model_validate(parameters)

        step_start = time.perf_counter()
        result_image = op(parent_image, params)
        step_ms = (time.perf_counter() - step_start) * 1000

        node_images[node_id] = result_image

        # 썸네일은 base64 data URL로 반환 (디스크 I/O 없음)
        thumb_px = thumbnail_size or THUMBNAIL_SIZE
        image_url = _encode_thumbnail(result_image, thumb_px)

        node_results.append(TreeNodeResult(
            node_id=node_id,
            image_url=image_url,
            execution_ms=round(step_ms, 2),
        ))

        # 자식 노드들을 스택에 추가
        children = children_map.get(node_id, [])
        for child in reversed(children):
            stack.append((child, result_image))

    total_ms = (time.perf_counter() - total_start) * 1000

    return TreeBatchResult(
        node_results=node_results,
        total_execution_ms=round(total_ms, 2),
    )
