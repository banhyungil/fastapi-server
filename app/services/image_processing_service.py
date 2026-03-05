from collections.abc import Callable
from typing import Any, Union

import cv2
import numpy as np
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from app.schemas.file import PrcType


# ── 파라미터 모델 ─────────────────────────────────────────────────────────────


class NoParams(BaseModel):
    """파라미터 없는 필터용."""
    model_config = ConfigDict(populate_by_name=True)


class KernelParams(BaseModel):
    """커널 크기만 사용하는 필터 (blur, medianBlur)."""
    model_config = ConfigDict(populate_by_name=True)
    kernel_size: int = Field(default=5, ge=1, alias="kernelSize", description="커널 크기 (홀수 권장)")


class SobelParams(BaseModel):
    """Sobel 엣지 검출 파라미터."""
    model_config = ConfigDict(populate_by_name=True)
    kernel_size: int = Field(default=3, ge=1, le=7, alias="kernelSize", description="커널 크기 (1~7 홀수)")
    dx: int = Field(default=1, ge=0, le=2, description="x방향 미분 차수 (0~2)")
    dy: int = Field(default=1, ge=0, le=2, description="y방향 미분 차수 (0~2)")
    scale: float = Field(default=1.0, description="미분 결과에 곱할 스케일 팩터")


class LaplacianParams(BaseModel):
    """Laplacian 엣지 검출 파라미터."""
    model_config = ConfigDict(populate_by_name=True)
    kernel_size: int = Field(default=3, ge=1, alias="kernelSize", description="커널 크기 (홀수)")
    scale: float = Field(default=1.0, description="미분 결과에 곱할 스케일 팩터")
    delta: float = Field(default=0.0, description="결과에 더할 오프셋 값")


class CannyParams(BaseModel):
    """Canny 엣지 검출 파라미터."""
    model_config = ConfigDict(populate_by_name=True)
    threshold1: float = Field(default=100.0, description="하위 임계값 (히스테리시스)")
    threshold2: float = Field(default=200.0, description="상위 임계값 (히스테리시스)")
    aperture_size: int = Field(default=3, ge=3, le=7, alias="apertureSize", description="Sobel 연산자 크기 (3~7 홀수)")


class GaussianBlurParams(BaseModel):
    """가우시안 블러 파라미터."""
    model_config = ConfigDict(populate_by_name=True)
    kernel_size: int = Field(default=5, ge=1, alias="kernelSize", description="커널 크기 (홀수)")
    sigma_x: float = Field(default=0.0, ge=0, alias="sigmaX", description="X방향 표준편차 (0이면 커널 크기로 자동 계산)")


class BilateralFilterParams(BaseModel):
    """양방향 필터 파라미터."""
    model_config = ConfigDict(populate_by_name=True)
    d: int = Field(default=9, ge=1, description="필터링 시 사용할 이웃 픽셀 직경")
    sigma_color: float = Field(default=75.0, ge=0, alias="sigmaColor", description="색상 공간 시그마 (클수록 더 넓은 색상 혼합)")
    sigma_space: float = Field(default=75.0, ge=0, alias="sigmaSpace", description="좌표 공간 시그마 (클수록 먼 픽셀도 영향)")


class BoxFilterParams(BaseModel):
    """박스 필터 파라미터."""
    model_config = ConfigDict(populate_by_name=True)
    kernel_size: int = Field(default=5, ge=1, alias="kernelSize", description="커널 크기")


class BrightnessParams(BaseModel):
    """밝기 조절 파라미터 (plus/minus)."""
    model_config = ConfigDict(populate_by_name=True)
    alpha: float = Field(default=1.0, ge=0, description="대비 계수 (1.0=원본, >1 대비 증가)")
    beta: float = Field(default=40.0, description="밝기 오프셋 (plus: 양수 적용, minus: 음수 적용)")


class GammaParams(BaseModel):
    """감마 보정 파라미터."""
    model_config = ConfigDict(populate_by_name=True)
    gamma: float = Field(default=1.0, gt=0, description="감마 값 (<1 밝게, >1 어둡게)")


class ThresholdParams(BaseModel):
    """이진화 임계값 파라미터 (binary/inverse/tozero/truncate/otsu)."""
    model_config = ConfigDict(populate_by_name=True)
    threshold_value: int = Field(default=127, ge=0, le=255, alias="thresholdValue", description="임계값 (0~255)")
    max_value: int = Field(default=255, ge=0, le=255, alias="maxValue", description="임계값 초과 시 적용할 최대값 (0~255)")


class AdaptiveThresholdParams(BaseModel):
    """적응형 임계값 파라미터."""
    model_config = ConfigDict(populate_by_name=True)
    max_value: int = Field(default=255, ge=0, le=255, alias="maxValue", description="임계값 초과 시 적용할 최대값 (0~255)")
    adaptive_method: str = Field(default="gaussian", alias="adaptiveMethod", description="적응형 방법 ('gaussian' 또는 'mean')")
    block_size: int = Field(default=11, ge=3, alias="blockSize", description="블록 크기 (홀수, 3 이상)")
    c: float = Field(default=2.0, description="평균/가중평균에서 차감할 상수")


class ContourParams(BaseModel):
    """윤곽선 검출 파라미터 (findContour/convexHull/boundingBox)."""
    model_config = ConfigDict(populate_by_name=True)
    threshold_value: int = Field(default=127, ge=0, le=255, alias="thresholdValue", description="이진화 임계값 (0~255)")
    color: list[int] = Field(default=[0, 255, 0], description="윤곽선 색상 [B, G, R]")
    thickness: int = Field(default=2, ge=1, description="윤곽선 두께 (px)")


class MorphologicalParams(BaseModel):
    """형태학적 연산 파라미터 (erosion/dilation/opening/closing)."""
    model_config = ConfigDict(populate_by_name=True)
    kernel_size: int = Field(default=5, ge=1, alias="kernelSize", description="커널 크기 (홀수 권장)")
    kernel_shape: str = Field(default="rect", alias="kernelShape", description="커널 모양 ('rect', 'ellipse', 'cross')")
    iterations: int = Field(default=1, ge=1, description="연산 반복 횟수")


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

AnyFilterParams = Union[
    SobelParams, LaplacianParams, CannyParams,
    GaussianBlurParams, KernelParams, BilateralFilterParams, BoxFilterParams,
    ContourParams,
    BrightnessParams, GammaParams,
    ThresholdParams, AdaptiveThresholdParams,
    MorphologicalParams,
    NoParams,
]

PARAMS_JSON_SCHEMA: dict[str, Any] = TypeAdapter(AnyFilterParams).json_schema(
    mode="validation", ref_template="#/$defs/{model}"
)

PARAM_MODELS: dict[PrcType, type[BaseModel]] = {
    # Edge Detection
    "sobel": SobelParams,
    "prewitt": NoParams,
    "laplacian": LaplacianParams,
    "canny": CannyParams,
    "roberts": NoParams,
    # Blurring
    "gaussian": GaussianBlurParams,
    "blur": KernelParams,
    "gaussianBlur": GaussianBlurParams,
    "medianBlur": KernelParams,
    "bilateralFilter": BilateralFilterParams,
    "boxFilter": BoxFilterParams,
    # Contour Detection
    "findContour": ContourParams,
    "convexHull": ContourParams,
    "boundingBox": ContourParams,
    # Brightness
    "plus": BrightnessParams,
    "minus": BrightnessParams,
    "gamma": GammaParams,
    "histogramEqualization": NoParams,
    # Thresholding
    "binary": ThresholdParams,
    "inverse": ThresholdParams,
    "tozero": ThresholdParams,
    "tozeroInverse": ThresholdParams,
    "truncate": ThresholdParams,
    "otsu": ThresholdParams,
    "adaptive": AdaptiveThresholdParams,
    # Morphological
    "erosion": MorphologicalParams,
    "dilation": MorphologicalParams,
    "opening": MorphologicalParams,
    "closing": MorphologicalParams,
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
