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
| Canny | - | - | 다단계 엣지 검출, 가장 정밀 |
| Roberts | - | - | 대각선 방향 미분 |

---

## 2. 블러링 (Blurring / Smoothing)

노이즈 제거, 이미지 부드럽게 처리.

| 필터 | prcType | 커널 기본값 | 특징 |
|------|---------|------------|------|
| ✅ 블러 (Average Blur) | `blur` | 5 | 단순 평균. 빠르지만 엣지 손실 큼 |
| ✅ 가우시안 블러 (Gaussian Blur) | `gaussianBlur` | 5 | 가우시안 가중 평균. 자연스러운 블러 |
| ✅ 중앙값 블러 (Median Blur) | `medianBlur` | 5 | 중앙값 사용. salt-and-pepper 노이즈 제거에 효과적 |
| ✅ 양방향 필터 (Bilateral Filter) | `bilateralFilter` | 9 | 엣지 보존 블러. 색상/공간 거리 동시 고려 |
| Box Filter | - | - | Average Blur와 유사, 정규화 옵션 있음 |

---

## 3. 윤곽선 검출 (Contour Detection)

객체의 외곽선을 찾아 표시.

| 필터 | prcType | 특징 |
|------|---------|------|
| ✅ Find Contour | `findContour` | 이진화 후 윤곽선 검출 및 시각화 |
| Convex Hull | - | 윤곽선의 볼록 껍질 |
| Bounding Box | - | 윤곽선의 외접 사각형 |

---

## 4. 밝기 변환 (Brightness)

픽셀 값에 상수를 더하거나 빼서 밝기 조절.

| 필터 | prcType | 특징 |
|------|---------|------|
| ✅ 밝기 증가 | `plus` | 픽셀 + 상수 (클리핑: max 255) |
| ✅ 밝기 감소 | `minus` | 픽셀 - 상수 (클리핑: min 0) |
| 감마 보정 | - | 비선형 밝기 변환 |
| 히스토그램 평탄화 | - | 밝기 분포 균등화 |

---

## 5. 이진화 (Thresholding)

픽셀을 임계값 기준으로 0 또는 255로 변환.

| 필터 | prcType | 특징 |
|------|---------|------|
| ✅ Binary | `binary` | 임계값 이상 → 255, 미만 → 0 |
| ✅ Inverse | `inverse` | Binary 반전 |
| ✅ Tozero | `tozero` | 임계값 미만 → 0, 이상 → 원본 유지 |
| ✅ TozeroInverse | `tozeroInverse` | Tozero 반전 |
| Truncate | - | 임계값 초과 → 임계값으로 클리핑 |
| Otsu | - | 자동 임계값 결정 |
| Adaptive | - | 영역별 로컬 임계값 적용 |

---

## 6. 형태학적 처리 (Morphological)

> 미구현 카테고리

| 필터 | 특징 |
|------|------|
| 침식 (Erosion) | 객체 축소, 노이즈 제거 |
| 팽창 (Dilation) | 객체 확장 |
| 열기 (Opening) | 침식 후 팽창. 작은 노이즈 제거 |
| 닫기 (Closing) | 팽창 후 침식. 작은 구멍 메움 |

---

## 필터별 조절 가능한 파라미터

> 각 OpenCV 함수가 지원하는 실험 가능한 파라미터 목록.
> 현재 코드에서 고정된 값은 **고정값**으로 표기.

---

### Edge Detection

#### `sobel` — `cv2.Sobel()`

| 파라미터 | 타입 | 현재 값 | 실험 범위 | 설명 |
|----------|------|---------|-----------|------|
| `ksize` | int | 3 | 1, 3, 5, 7 | 커널 크기 (홀수, 최대 7) |
| `dx` | int | 1 | 0, 1, 2 | x 방향 미분 차수 |
| `dy` | int | 1 | 0, 1, 2 | y 방향 미분 차수 |
| `scale` | float | 1 | 0.5 ~ 4.0 | 미분 결과에 곱하는 스케일 |
| `delta` | float | 0 | -128 ~ 128 | 결과에 더하는 오프셋 |
| `borderType` | enum | `BORDER_DEFAULT` | `BORDER_REPLICATE`, `BORDER_REFLECT`, `BORDER_CONSTANT` 등 | 경계 처리 방식 |

#### `prewitt` — `cv2.filter2D()`

| 파라미터 | 타입 | 현재 값 | 실험 범위 | 설명 |
|----------|------|---------|-----------|------|
| `kernel` | ndarray | 고정 3x3 | 커스텀 커널 | Prewitt 연산자 (현재 하드코딩) |
| `delta` | float | 0 | -128 ~ 128 | 결과에 더하는 오프셋 |
| `borderType` | enum | `BORDER_DEFAULT` | `BORDER_REPLICATE`, `BORDER_REFLECT` 등 | 경계 처리 방식 |

#### `laplacian` — `cv2.Laplacian()`

| 파라미터 | 타입 | 현재 값 | 실험 범위 | 설명 |
|----------|------|---------|-----------|------|
| `ksize` | int | 3 | 1, 3, 5, 7 | 커널 크기 (홀수) |
| `scale` | float | 1 | 0.5 ~ 4.0 | 미분 결과 스케일 |
| `delta` | float | 0 | -128 ~ 128 | 결과 오프셋 |
| `borderType` | enum | `BORDER_DEFAULT` | `BORDER_REPLICATE`, `BORDER_REFLECT` 등 | 경계 처리 방식 |

---

### Blurring

#### `blur` — `cv2.blur()`

| 파라미터 | 타입 | 현재 값 | 실험 범위 | 설명 |
|----------|------|---------|-----------|------|
| `ksize` | (int, int) | (5, 5) | (1,1) ~ (31,31) | 커널 크기 (홀짝 무관, 비대칭 가능) |
| `anchor` | (int, int) | (-1, -1) = 중심 | 커널 내 좌표 | 앵커 포인트 위치 |
| `borderType` | enum | `BORDER_DEFAULT` | `BORDER_REPLICATE`, `BORDER_REFLECT` 등 | 경계 처리 방식 |

#### `gaussian` / `gaussianBlur` — `cv2.GaussianBlur()`

| 파라미터 | 타입 | 현재 값 | 실험 범위 | 설명 |
|----------|------|---------|-----------|------|
| `ksize` | (int, int) | (5, 5) | (1,1) ~ (31,31) | 커널 크기 (홀수, 비대칭 가능) |
| `sigmaX` | float | **고정 0** | 0.1 ~ 10.0 | x 방향 가우시안 표준편차 (0이면 ksize로 자동 계산) |
| `sigmaY` | float | 0 (= sigmaX) | 0.1 ~ 10.0 | y 방향 표준편차 (0이면 sigmaX와 동일) |
| `borderType` | enum | `BORDER_DEFAULT` | `BORDER_REPLICATE`, `BORDER_REFLECT` 등 | 경계 처리 방식 |

#### `medianBlur` — `cv2.medianBlur()`

| 파라미터 | 타입 | 현재 값 | 실험 범위 | 설명 |
|----------|------|---------|-----------|------|
| `ksize` | int | 5 | 3, 5, 7, ..., 31 | 커널 크기 (홀수만 가능) |

#### `bilateralFilter` — `cv2.bilateralFilter()`

| 파라미터 | 타입 | 현재 값 | 실험 범위 | 설명 |
|----------|------|---------|-----------|------|
| `d` | int | 9 | 1 ~ 15 | 필터 직경 (-1이면 sigmaSpace로 자동 계산) |
| `sigmaColor` | float | **고정 75** | 10 ~ 200 | 색상 공간 필터 시그마. 클수록 더 넓은 색상 범위를 혼합 |
| `sigmaSpace` | float | **고정 75** | 10 ~ 200 | 좌표 공간 필터 시그마. 클수록 더 먼 픽셀이 영향 |
| `borderType` | enum | `BORDER_DEFAULT` | `BORDER_REPLICATE`, `BORDER_REFLECT` 등 | 경계 처리 방식 |

---

### Contour Detection

#### `findContour` — `cv2.threshold()` + `cv2.findContours()` + `cv2.drawContours()`

| 파라미터 | 타입 | 현재 값 | 실험 범위 | 설명 |
|----------|------|---------|-----------|------|
| `threshold` | int | **고정 127** | 0 ~ 255 | 이진화 임계값 |
| `maxval` | int | **고정 255** | 1 ~ 255 | 이진화 최대값 |
| `mode` | enum | **고정 `RETR_EXTERNAL`** | `RETR_LIST`, `RETR_TREE`, `RETR_CCOMP` | 윤곽선 검색 모드 |
| `method` | enum | **고정 `CHAIN_APPROX_SIMPLE`** | `CHAIN_APPROX_NONE`, `CHAIN_APPROX_TC89_L1` | 윤곽선 근사 방법 |
| `color` | (B,G,R) | **고정 (0,255,0)** | 임의 색상 | 윤곽선 색상 |
| `thickness` | int | **고정 2** | 1 ~ 10, -1(채우기) | 윤곽선 두께 |

---

### Brightness

#### `plus` / `minus` — `cv2.convertScaleAbs()`

| 파라미터 | 타입 | 현재 값 | 실험 범위 | 설명 |
|----------|------|---------|-----------|------|
| `alpha` | float | **고정 1.0** | 0.0 ~ 3.0 | 대비(contrast) 계수. `result = alpha * pixel + beta` |
| `beta` | float | **고정 ±40** | -255 ~ 255 | 밝기(brightness) 오프셋 |

---

### Thresholding

#### `binary` / `inverse` / `tozero` / `tozeroInverse` — `cv2.threshold()`

| 파라미터 | 타입 | 현재 값 | 실험 범위 | 설명 |
|----------|------|---------|-----------|------|
| `thresh` | int | **고정 127** | 0 ~ 255 | 임계값 |
| `maxval` | int | **고정 255** | 1 ~ 255 | 임계값 초과 시 할당할 값 (binary/inverse에서 사용) |
