from collections.abc import Callable

import cv2
import numpy as np


# 타입은 PascalCase로 작성
ImageOperation = Callable[[np.ndarray], np.ndarray]


THRESHOLD_TYPE_MAP: dict[str, int] = {
    "binary": cv2.THRESH_BINARY,
    "inverse": cv2.THRESH_BINARY_INV,
    "tozero": cv2.THRESH_TOZERO,
    "tozeroInverse": cv2.THRESH_TOZERO_INV,
}


# _<name>: 해당 모듈 내부용 변수
def _to_gray(image: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def _op_sobel(image: np.ndarray) -> np.ndarray:
    gray = _to_gray(image)
    grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    magnitude = cv2.magnitude(grad_x, grad_y)
    return cv2.convertScaleAbs(magnitude)


def _op_prewitt(image: np.ndarray) -> np.ndarray:
    gray = _to_gray(image)
    kernel_x = np.array([[1, 0, -1], [1, 0, -1], [1, 0, -1]], dtype=np.float32)
    kernel_y = np.array([[1, 1, 1], [0, 0, 0], [-1, -1, -1]], dtype=np.float32)
    prewitt_x = cv2.filter2D(gray, cv2.CV_32F, kernel_x)
    prewitt_y = cv2.filter2D(gray, cv2.CV_32F, kernel_y)
    magnitude = cv2.magnitude(prewitt_x, prewitt_y)
    return cv2.convertScaleAbs(magnitude)


def _op_laplacian(image: np.ndarray) -> np.ndarray:
    gray = _to_gray(image)
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    return cv2.convertScaleAbs(laplacian)


def _op_gaussian(image: np.ndarray) -> np.ndarray:
    return cv2.GaussianBlur(image, (5, 5), 0)


def _op_blur(image: np.ndarray) -> np.ndarray:
    return cv2.blur(image, (5, 5))


def _op_gaussian_blur(image: np.ndarray) -> np.ndarray:
    return cv2.GaussianBlur(image, (5, 5), 0)


def _op_median_blur(image: np.ndarray) -> np.ndarray:
    return cv2.medianBlur(image, 5)


def _op_bilateral_filter(image: np.ndarray) -> np.ndarray:
    return cv2.bilateralFilter(image, d=9, sigmaColor=75, sigmaSpace=75)


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


OPERATIONS: dict[str, ImageOperation] = {
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


def process_image(prc_type: str, image_bytes: bytes) -> bytes:
    if not image_bytes:
        raise ValueError("empty image payload")

    image_array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("invalid image payload")

    operation = OPERATIONS.get(prc_type)
    if operation is None:
        raise ValueError(f"unsupported prcType: {prc_type}")

    processed = operation(image)
    success, encoded = cv2.imencode(".png", processed)
    if not success:
        raise RuntimeError("failed to encode processed image")

    return encoded.tobytes()
