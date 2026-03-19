from typing import Any, Union

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from app.schemas.file import FilterType


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


class CustomFilterParams(BaseModel):
    """커스텀 필터 파라미터."""
    model_config = ConfigDict(populate_by_name=True)
    filter_id: str = Field(..., alias="filterId", description="커스텀 필터 ID (UUID)")
    parameters: dict[str, Any] = Field(default_factory=dict, description="사용자 정의 파라미터")


# ── 유니온 타입 & JSON 스키마 ──────────────────────────────────────────────────

AnyFilterParams = Union[
    SobelParams, LaplacianParams, CannyParams,
    GaussianBlurParams, KernelParams, BilateralFilterParams, BoxFilterParams,
    ContourParams,
    BrightnessParams, GammaParams,
    ThresholdParams, AdaptiveThresholdParams,
    MorphologicalParams,
    CustomFilterParams,
    NoParams,
]

PARAMS_JSON_SCHEMA: dict[str, Any] = TypeAdapter(AnyFilterParams).json_schema(
    mode="validation", ref_template="#/$defs/{model}"
)

# ── FilterType → 파라미터 모델 매핑 ─────────────────────────────────────────────

PARAM_MODELS: dict[FilterType, type[BaseModel]] = {
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
    # Custom
    "custom": CustomFilterParams,
}
