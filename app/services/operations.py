"""순수 이미지 필터 연산 함수 + OPERATIONS 매핑."""

from collections.abc import Callable

import cv2
import numpy as np

from app.schemas.file import FilterType
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

ImageOperation = Callable[..., np.ndarray]


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
    from app.repos.custom_filters_repo import get_custom_filter_by_id
    from app.services.custom_filters_service import execute_custom_filter

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

OPERATIONS: dict[FilterType, ImageOperation] = {
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
