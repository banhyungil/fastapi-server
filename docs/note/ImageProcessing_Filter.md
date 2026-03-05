# 영상처리 필터 종류

✅ = 구현됨

---

## 1. 필터링 (Edge Detection)

엣지(윤곽선)를 검출하는 미분 기반 필터.

| 필터 | prcType | 커널 기본값 | 특징 |
|------|---------|------------|------|
| ✅ 소벨 (Sobel) | `sobel` | 3 | x/y 방향 1차 미분. 노이즈에 비교적 강함 |
| ✅ 프르윗 (Prewitt) | `prewitt` | - | Sobel과 유사, 가중치 균일 |
| ✅ 라플라시안 (Laplacian) | `laplacian` | 3 | 2차 미분. 방향 무관 엣지 검출, 노이즈에 민감 |
| ✅ 가우시안 (Gaussian) | `gaussian` | 5 | 스무딩 후 엣지 강조 (LoG 방식) |
| ✅ Canny | `canny` | - | 다단계 엣지 검출, 가장 정밀 |
| ✅ Roberts | `roberts` | - | 대각선 방향 미분 |

---

## 2. 블러링 (Blurring / Smoothing)

노이즈 제거, 이미지 부드럽게 처리.

| 필터 | prcType | 커널 기본값 | 특징 |
|------|---------|------------|------|
| ✅ 블러 (Average Blur) | `blur` | 5 | 단순 평균. 빠르지만 엣지 손실 큼 |
| ✅ 가우시안 블러 (Gaussian Blur) | `gaussianBlur` | 5 | 가우시안 가중 평균. 자연스러운 블러 |
| ✅ 중앙값 블러 (Median Blur) | `medianBlur` | 5 | 중앙값 사용. salt-and-pepper 노이즈 제거에 효과적 |
| ✅ 양방향 필터 (Bilateral Filter) | `bilateralFilter` | 9 | 엣지 보존 블러. 색상/공간 거리 동시 고려 |
| ✅ Box Filter | `boxFilter` | 5 | Average Blur와 유사, 정규화 옵션 있음 |

---

## 3. 윤곽선 검출 (Contour Detection)

객체의 외곽선을 찾아 표시.

| 필터 | prcType | 특징 |
|------|---------|------|
| ✅ Find Contour | `findContour` | 이진화 후 윤곽선 검출 및 시각화 |
| ✅ Convex Hull | `convexHull` | 윤곽선의 볼록 껍질 |
| ✅ Bounding Box | `boundingBox` | 윤곽선의 외접 사각형 |

---

## 4. 밝기 변환 (Brightness)

픽셀 값에 상수를 더하거나 빼서 밝기 조절.

| 필터 | prcType | 특징 |
|------|---------|------|
| ✅ 밝기 증가 | `plus` | 픽셀 + 상수 (클리핑: max 255) |
| ✅ 밝기 감소 | `minus` | 픽셀 - 상수 (클리핑: min 0) |
| ✅ 감마 보정 | `gamma` | 비선형 밝기 변환 |
| ✅ 히스토그램 평탄화 | `histogramEqualization` | 밝기 분포 균등화 |

---

## 5. 이진화 (Thresholding)

픽셀을 임계값 기준으로 0 또는 255로 변환.

| 필터 | prcType | 특징 |
|------|---------|------|
| ✅ Binary | `binary` | 임계값 이상 → 255, 미만 → 0 |
| ✅ Inverse | `inverse` | Binary 반전 |
| ✅ Tozero | `tozero` | 임계값 미만 → 0, 이상 → 원본 유지 |
| ✅ TozeroInverse | `tozeroInverse` | Tozero 반전 |
| ✅ Truncate | `truncate` | 임계값 초과 → 임계값으로 클리핑 |
| ✅ Otsu | `otsu` | 자동 임계값 결정 |
| ✅ Adaptive | `adaptive` | 영역별 로컬 임계값 적용 |

---

## 6. 형태학적 처리 (Morphological)

| 필터 | prcType | 특징 |
|------|---------|------|
| ✅ 침식 (Erosion) | `erosion` | 객체 축소, 노이즈 제거 |
| ✅ 팽창 (Dilation) | `dilation` | 객체 확장 |
| ✅ 열기 (Opening) | `opening` | 침식 후 팽창. 작은 노이즈 제거 |
| ✅ 닫기 (Closing) | `closing` | 팽창 후 침식. 작은 구멍 메움 |

---

## 필터별 조절 가능한 파라미터

> `parameters` JSON 필드로 전달. 생략 시 기본값 사용.

---

### Edge Detection

#### `sobel` — `cv2.Sobel()`

| 파라미터 | 타입 | 기본값 | 범위 | 설명 |
|----------|------|--------|------|------|
| `kernelSize` | int | 3 | 1, 3, 5, 7 | 커널 크기 (홀수, 최대 7) |
| `dx` | int | 1 | 0, 1, 2 | x 방향 미분 차수 |
| `dy` | int | 1 | 0, 1, 2 | y 방향 미분 차수 |
| `scale` | float | 1.0 | 0.5 ~ 4.0 | 미분 결과에 곱하는 스케일 |

#### `prewitt` — `cv2.filter2D()`

파라미터 없음. 고정 3x3 Prewitt 커널 사용.

#### `laplacian` — `cv2.Laplacian()`

| 파라미터 | 타입 | 기본값 | 범위 | 설명 |
|----------|------|--------|------|------|
| `kernelSize` | int | 3 | 1, 3, 5, 7 | 커널 크기 (홀수) |
| `scale` | float | 1.0 | 0.5 ~ 4.0 | 미분 결과 스케일 |
| `delta` | float | 0.0 | -128 ~ 128 | 결과 오프셋 |

#### `canny` — `cv2.Canny()`

| 파라미터 | 타입 | 기본값 | 범위 | 설명 |
|----------|------|--------|------|------|
| `threshold1` | float | 100.0 | 0 ~ 500 | 하단 임계값 |
| `threshold2` | float | 200.0 | 0 ~ 500 | 상단 임계값 |
| `apertureSize` | int | 3 | 3, 5, 7 | Sobel 연산자 크기 |

#### `roberts` — `cv2.filter2D()`

파라미터 없음. 고정 2x2 Roberts cross 커널 사용.

---

### Blurring

#### `blur` — `cv2.blur()`

| 파라미터 | 타입 | 기본값 | 범위 | 설명 |
|----------|------|--------|------|------|
| `kernelSize` | int | 5 | 1 ~ 31 | 커널 크기 (홀짝 무관) |

#### `gaussian` / `gaussianBlur` — `cv2.GaussianBlur()`

| 파라미터 | 타입 | 기본값 | 범위 | 설명 |
|----------|------|--------|------|------|
| `kernelSize` | int | 5 | 1 ~ 31 | 커널 크기 (홀수) |
| `sigmaX` | float | 0.0 | 0 ~ 10.0 | 가우시안 표준편차 (0이면 ksize로 자동 계산) |

#### `medianBlur` — `cv2.medianBlur()`

| 파라미터 | 타입 | 기본값 | 범위 | 설명 |
|----------|------|--------|------|------|
| `kernelSize` | int | 5 | 3 ~ 31 | 커널 크기 (홀수) |

#### `bilateralFilter` — `cv2.bilateralFilter()`

| 파라미터 | 타입 | 기본값 | 범위 | 설명 |
|----------|------|--------|------|------|
| `d` | int | 9 | 1 ~ 15 | 필터 직경 |
| `sigmaColor` | float | 75.0 | 10 ~ 200 | 색상 공간 시그마 |
| `sigmaSpace` | float | 75.0 | 10 ~ 200 | 좌표 공간 시그마 |

#### `boxFilter` — `cv2.boxFilter()`

| 파라미터 | 타입 | 기본값 | 범위 | 설명 |
|----------|------|--------|------|------|
| `kernelSize` | int | 5 | 1 ~ 31 | 커널 크기 |

---

### Contour Detection

#### `findContour` / `convexHull` / `boundingBox`

| 파라미터 | 타입 | 기본값 | 범위 | 설명 |
|----------|------|--------|------|------|
| `thresholdValue` | int | 127 | 0 ~ 255 | 이진화 임계값 |
| `color` | [B,G,R] | [0,255,0] | 임의 | 윤곽선/도형 색상 |
| `thickness` | int | 2 | 1 ~ 10 | 선 두께 |

---

### Brightness

#### `plus` / `minus` — `cv2.convertScaleAbs()`

| 파라미터 | 타입 | 기본값 | 범위 | 설명 |
|----------|------|--------|------|------|
| `alpha` | float | 1.0 | 0.0 ~ 3.0 | 대비(contrast) 계수 |
| `beta` | float | 40.0 | 0 ~ 255 | 밝기 오프셋 (minus는 자동 음수 처리) |

#### `gamma` — `cv2.LUT()`

| 파라미터 | 타입 | 기본값 | 범위 | 설명 |
|----------|------|--------|------|------|
| `gamma` | float | 1.0 | 0.1 ~ 5.0 | 감마값. <1 밝게, >1 어둡게 |

#### `histogramEqualization` — `cv2.equalizeHist()`

파라미터 없음.

---

### Thresholding

#### `binary` / `inverse` / `tozero` / `tozeroInverse` / `truncate` — `cv2.threshold()`

| 파라미터 | 타입 | 기본값 | 범위 | 설명 |
|----------|------|--------|------|------|
| `thresholdValue` | int | 127 | 0 ~ 255 | 임계값 |
| `maxValue` | int | 255 | 1 ~ 255 | 할당 최대값 |

#### `otsu` — `cv2.threshold(THRESH_OTSU)`

| 파라미터 | 타입 | 기본값 | 범위 | 설명 |
|----------|------|--------|------|------|
| `maxValue` | int | 255 | 1 ~ 255 | 할당 최대값 (임계값은 자동 결정) |

#### `adaptive` — `cv2.adaptiveThreshold()`

| 파라미터 | 타입 | 기본값 | 범위 | 설명 |
|----------|------|--------|------|------|
| `maxValue` | int | 255 | 1 ~ 255 | 할당 최대값 |
| `adaptiveMethod` | str | "gaussian" | "gaussian", "mean" | 적응형 방법 |
| `blockSize` | int | 11 | 3 이상 홀수 | 로컬 영역 크기 |
| `c` | float | 2.0 | -10 ~ 10 | 평균에서 빼는 상수 |

---

### Morphological

#### `erosion` / `dilation` / `opening` / `closing`

| 파라미터 | 타입 | 기본값 | 범위 | 설명 |
|----------|------|--------|------|------|
| `kernelSize` | int | 5 | 1 ~ 31 | 구조 요소 크기 (홀수) |
| `kernelShape` | str | "rect" | "rect", "ellipse", "cross" | 구조 요소 형태 |
| `iterations` | int | 1 | 1 ~ 10 | 반복 횟수 |
