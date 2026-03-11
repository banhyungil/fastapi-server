# pyvips 사용 정리

## 개요

pyvips는 libvips의 Python 바인딩. **스트리밍(lazy) 아키텍처**로 이미지 전체를 메모리에 올리지 않고 청크 단위로 처리한다. 대용량 이미지(8K+) 처리에 적합.

---

## Windows 환경 설정

```python
import os
import sys

# Windows에서는 libvips DLL 경로를 수동 등록해야 함
vips_bin = Path(os.environ.get("VIPS_HOME", "")) / "bin"

# winget으로 설치한 경우 기본 경로 탐색
winget_base = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/WinGet/Packages"
for d in winget_base.glob("libvips*"):
    candidate = next(d.glob("vips-dev-*/bin"), None)

# DLL 검색 경로에 추가
os.add_dll_directory(str(vips_bin))
os.environ["PATH"] = str(vips_bin) + os.pathsep + os.environ.get("PATH", "")
```

---

## 이미지 로드

```python
import pyvips

# 파일에서 로드 — lazy, 전체 메모리 적재 안 함 (스트리밍)
img = pyvips.Image.new_from_file("image.tiff")

# numpy ndarray(OpenCV)에서 변환 — 메모리 복사 발생
# new_from_memory(data, width, height, bands, format)
vips_img = pyvips.Image.new_from_memory(
    image.tobytes(),       # numpy → bytes 변환 (메모리 복사)
    image.shape[1],        # width
    image.shape[0],        # height
    image.shape[2],        # bands (채널 수: RGB=3, grayscale=1)
    "uchar",               # uint8 포맷
)
```

> **주의**: OpenCV는 BGR, pyvips는 RGB. 변환 필요:
> ```python
> rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
> ```

---

## DZI 타일 생성

```python
# DZI (Deep Zoom Image) 타일로 분할 저장
# 결과: {base}.dzi 메타파일 + {base}_files/ 디렉토리에 피라미드 타일
vips_img.dzsave(
    "output/node_id",      # 기본 경로 (확장자 없이)
    tile_size=256,          # 타일 한 변 크기 (px)
    overlap=1,              # 타일 간 겹침 (px) — 경계 이음새 방지
    suffix=".jpg[Q=85]",   # 타일 포맷 + 품질
)
```

### dzsave 주요 옵션

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `tile_size` | 타일 크기 (px) | 256 |
| `overlap` | 타일 겹침 (px) | 1 |
| `suffix` | 타일 파일 포맷 | `".jpeg"` |
| `depth` | 피라미드 깊이 | `"onetile"` (최상위 레벨이 1타일) |
| `layout` | 타일 레이아웃 | `"dz"` (Deep Zoom) |

### suffix 포맷 예시

```python
suffix=".jpg[Q=85]"        # JPEG 품질 85
suffix=".webp[Q=80]"       # WebP 품질 80 — JPEG 대비 25~35% 용량 절감
suffix=".png"              # PNG 무손실
```

---

## DZI 출력 구조

```
output/node_id.dzi              ← XML 메타파일 (크기, 타일 정보)
output/node_id_files/
  ├── 0/                        ← 최저 해상도 레벨 (1x1 타일)
  │   └── 0_0.jpg
  ├── 1/
  │   └── 0_0.jpg
  ├── ...
  └── 13/                       ← 최고 해상도 레벨 (원본 크기)
      ├── 0_0.jpg
      ├── 1_0.jpg
      ├── 0_1.jpg
      └── ...
```

- 레벨 번호가 클수록 고해상도
- 프론트엔드(OpenSeadragon)가 현재 줌 레벨에 맞는 타일만 요청

---

## 현재 프로젝트 적용

```python
# _save_node_dzi() 핵심 흐름

# 1. OpenCV ndarray → pyvips 변환
if image.ndim == 2:  # grayscale
    vips_img = pyvips.Image.new_from_memory(
        image.tobytes(), width, height, 1, "uchar",
    )
else:  # BGR → RGB 변환 후
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    vips_img = pyvips.Image.new_from_memory(
        rgb.tobytes(), width, height, channels, "uchar",
    )

# 2. 기존 타일 제거 후 재생성
shutil.rmtree(tiles_dir, ignore_errors=True)

# 3. DZI 타일 생성
vips_img.dzsave(dzi_base, tile_size=256, overlap=1, suffix=".jpg[Q=85]")

# 4. URL 반환 — 캐시 버스팅용 타임스탬프 포함
return f"/{dzi_base}.dzi?t={timestamp}"
```

### 조건

- `max(height, width) >= 4000px` 이면 DZI 타일 생성
- 그 미만이면 원본 PNG로 저장 (타일링 불필요)
