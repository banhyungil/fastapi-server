# 요청 바디 스키마 생성

## 배경

현재 `/image-processing` POST 엔드포인트의 Form 필드들은 개별 파라미터로 선언되어 있어,
OpenAPI에서 자동 생성된 이름(`Body_img_processing_api_image_processing_post`)으로 표현된다.

Form 필드들을 Pydantic 모델로 묶으면 **명시적인 스키마 이름**이 부여된다.

> FastAPI 0.113.0+에서 지원

---

## 현재 방식 vs 스키마 방식

### 현재 (개별 Form 파라미터)

```python
async def img_processing(
    file: UploadFile = File(...),
    prc_type: PrcType = Form(..., alias="prcType"),
    kernel_size: int | None = Form(None, alias="kernelSize"),
) -> StreamingResponse:
```

OpenAPI 스키마 이름: `Body_img_processing_api_image_processing_post` (자동 생성)

### 변경 후 (Pydantic Form 모델)

```python
async def img_processing(
    file: UploadFile = File(...),
    form: Annotated[ImgProcessingForm, Form()],
) -> StreamingResponse:
```

OpenAPI 스키마 이름: `ImgProcessingForm` (명시적)

---

## 구현 방법

### 1. `schemas/file.py`에 Form 모델 추가

```python
from typing import Annotated
from app.services.image_processing_service import PrcType

class ImgProcessingForm(CamelModel):
    prc_type: PrcType
    kernel_size: int | None = None
```

- `CamelModel`을 상속하면 `alias_generator`에 의해 `prcType`, `kernelSize`로 자동 변환됨
- `prc_type: PrcType` → Form 필드 이름 `prcType`, enum 검증 포함
- `kernel_size: int | None = None` → Form 필드 이름 `kernelSize`, 선택 필드

### 2. 엔드포인트 수정

```python
from typing import Annotated
from app.schemas.file import ImgProcessingForm

@router.post("/image-processing", tags=["img-processing"])
async def img_processing(
    file: UploadFile = File(...),
    form: Annotated[ImgProcessingForm, Form()],
) -> StreamingResponse:
    uploaded_file_bytes = await file.read()

    try:
        processed_image_bytes = process_image(
            prc_type=form.prc_type,
            image_bytes=uploaded_file_bytes,
            kernel_size=form.kernel_size,
        )
    ...
```

---

## OpenAPI 변환 결과

```json
"components": {
  "schemas": {
    "ImgProcessingForm": {
      "type": "object",
      "properties": {
        "prcType": {
          "type": "string",
          "enum": ["sobel", "prewitt", "laplacian", ...]
        },
        "kernelSize": {
          "anyOf": [{"type": "integer"}, {"type": "null"}]
        }
      },
      "required": ["prcType"]
    }
  }
}
```

---

## TypeScript 타입 사용 예시

`pnpm gen:types` 실행 후:

```typescript
import type { components } from 'src/types/api.d';

type ImgProcessingForm = components['schemas']['ImgProcessingForm'];
// → { prcType: "sobel" | "prewitt" | ...; kernelSize?: number | null }

type PrcType = ImgProcessingForm['prcType'];
// → "sobel" | "prewitt" | "laplacian" | ...
```

---

## 주의사항

- `file: UploadFile`은 모델에 포함 불가 → 반드시 별도 파라미터로 유지
- `Form()` 어노테이션은 FastAPI 0.113.0 이상 필요 (현재 0.133.0 ✅)
- 순환 참조 주의: `schemas/file.py`에서 `image_processing_service`를 import하면
  `service → schemas` 방향의 의존성이 생김
  → `PrcType`을 `schemas/file.py`로 이동하거나 별도 `schemas/common.py`로 분리 권장
