from collections.abc import Callable
import inspect

import cv2
import numpy as np

from app.schemas.file import PrcType
from app.utils.timing import measure_time


ImageOperation = Callable[..., np.ndarray]


THRESHOLD_TYPE_MAP: dict[str, int] = {
    "binary": cv2.THRESH_BINARY,
    "inverse": cv2.THRESH_BINARY_INV,
    "tozero": cv2.THRESH_TOZERO,
    "tozeroInverse": cv2.THRESH_TOZERO_INV,
}

# kernel_size를 사용하는 연산의 기본값을 한 곳에서 관리
DEFAULT_KERNEL_SIZES: dict[PrcType, int] = {
    "sobel": 3,
    "laplacian": 3,
    "gaussian": 5,
    "blur": 5,
    "gaussianBlur": 5,
    "medianBlur": 5,
    "bilateralFilter": 9,
}


def _to_gray(image: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def _ensure_odd(k: int) -> int:
    k = max(1, k)
    return k if k % 2 == 1 else k + 1


# ── kernel_size 사용하는 연산 ──────────────────────────────────────────────────

def _op_sobel(image: np.ndarray, kernel_size: int) -> np.ndarray:
    k = _ensure_odd(min(kernel_size, 7))  # Sobel ksize 최대 7
    gray = _to_gray(image)
    grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=k)
    grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=k)
    magnitude = cv2.magnitude(grad_x, grad_y)
    return cv2.convertScaleAbs(magnitude)


def _op_laplacian(image: np.ndarray, kernel_size: int) -> np.ndarray:
    k = _ensure_odd(kernel_size)
    gray = _to_gray(image)
    laplacian = cv2.Laplacian(gray, cv2.CV_64F, ksize=k)
    return cv2.convertScaleAbs(laplacian)


def _op_gaussian(image: np.ndarray, kernel_size: int) -> np.ndarray:
    k = _ensure_odd(kernel_size)
    return cv2.GaussianBlur(image, (k, k), 0)


def _op_blur(image: np.ndarray, kernel_size: int) -> np.ndarray:
    k = max(1, kernel_size)
    return cv2.blur(image, (k, k))


def _op_gaussian_blur(image: np.ndarray, kernel_size: int) -> np.ndarray:
    k = _ensure_odd(kernel_size)
    return cv2.GaussianBlur(image, (k, k), 0)


def _op_median_blur(image: np.ndarray, kernel_size: int) -> np.ndarray:
    k = _ensure_odd(kernel_size)
    return cv2.medianBlur(image, k)


def _op_bilateral_filter(image: np.ndarray, kernel_size: int) -> np.ndarray:
    return cv2.bilateralFilter(image, d=kernel_size, sigmaColor=75, sigmaSpace=75)


# ── kernel_size 미사용 연산 ────────────────────────────────────────────────────

def _op_prewitt(image: np.ndarray) -> np.ndarray:
    gray = _to_gray(image)
    kernel_x = np.array([[1, 0, -1], [1, 0, -1], [1, 0, -1]], dtype=np.float32)
    kernel_y = np.array([[1, 1, 1], [0, 0, 0], [-1, -1, -1]], dtype=np.float32)
    prewitt_x = cv2.filter2D(gray, cv2.CV_32F, kernel_x)
    prewitt_y = cv2.filter2D(gray, cv2.CV_32F, kernel_y)
    magnitude = cv2.magnitude(prewitt_x, prewitt_y)
    return cv2.convertScaleAbs(magnitude)


def _op_find_contour(image: np.ndarray) -> np.ndarray:
    gray = _to_gray(image)
    _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contour_image = image.copy()
    cv2.drawContours(contour_image, contours, -1, (0, 255, 0), 2)
    return contour_image


def _op_brightness_plus(image: np.ndarray) -> np.ndarray:
    return cv2.convertScaleAbs(image, alpha=1.0, beta=40)


def _op_brightness_minus(image: np.ndarray) -> np.ndarray:
    return cv2.convertScaleAbs(image, alpha=1.0, beta=-40)


def _op_threshold(image: np.ndarray, threshold_type: int) -> np.ndarray:
    gray = _to_gray(image)
    _, result = cv2.threshold(gray, 127, 255, threshold_type)
    return result


def _op_threshold_binary(image: np.ndarray) -> np.ndarray:
    return _op_threshold(image, THRESHOLD_TYPE_MAP["binary"])


def _op_threshold_inverse(image: np.ndarray) -> np.ndarray:
    return _op_threshold(image, THRESHOLD_TYPE_MAP["inverse"])


def _op_threshold_tozero(image: np.ndarray) -> np.ndarray:
    return _op_threshold(image, THRESHOLD_TYPE_MAP["tozero"])


def _op_threshold_tozero_inverse(image: np.ndarray) -> np.ndarray:
    return _op_threshold(image, THRESHOLD_TYPE_MAP["tozeroInverse"])


OPERATIONS: dict[PrcType, ImageOperation] = {
    "sobel": _op_sobel,
    "prewitt": _op_prewitt,
    "laplacian": _op_laplacian,
    "gaussian": _op_gaussian,
    "blur": _op_blur,
    "gaussianBlur": _op_gaussian_blur,
    "medianBlur": _op_median_blur,
    "bilateralFilter": _op_bilateral_filter,
    "findContour": _op_find_contour,
    "plus": _op_brightness_plus,
    "minus": _op_brightness_minus,
    "binary": _op_threshold_binary,
    "inverse": _op_threshold_inverse,
    "tozero": _op_threshold_tozero,
    "tozeroInverse": _op_threshold_tozero_inverse,
}

def process_image(prc_type: PrcType, image_bytes: bytes, kernel_size: int | None = None) -> bytes:
    if not image_bytes:
        raise ValueError("empty image payload")

    image_array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("invalid image payload")

    op = OPERATIONS.get(prc_type)
    if op is None:
        raise ValueError(f"unsupported prcType: {prc_type}")

    if "kernel_size" in inspect.signature(op).parameters:
        k = kernel_size if kernel_size is not None else DEFAULT_KERNEL_SIZES[prc_type]
        processed = op(image, k)
    else:
        processed = op(image)

    success, encoded = cv2.imencode(".png", processed)
    if not success:
        raise RuntimeError("failed to encode processed image")

    return encoded.tobytes()
