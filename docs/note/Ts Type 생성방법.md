# TypeScript 타입 자동 생성

## 개요

FastAPI가 라우터의 타입 어노테이션을 기반으로 OpenAPI 스키마를 자동 생성하고,
`openapi-typescript`가 이를 TypeScript 타입으로 변환한다.

```
FastAPI 라우터 어노테이션
    → /openapi.json (자동 생성)
    → openapi-typescript
    → src/types/api.d.ts
```

---

## 사전 준비

### quasar 프로젝트 (`quasar-image-processing`)

`package.json`에 추가:

```json
{
  "scripts": {
    "gen:types": "openapi-typescript http://localhost:8000/openapi.json -o src/types/api.d.ts"
  },
  "devDependencies": {
    "openapi-typescript": "^7.6.1"
  }
}
```

설치:
```bash
pnpm install
```

---

## 타입 생성 방법

1. FastAPI 서버 실행 (`F5` 또는 `fastapi dev`)
2. 타입 생성 스크립트 실행:

```bash
pnpm gen:types
```

`src/types/api.d.ts` 파일이 생성됨.

---

## 생성 결과 구조

```typescript
// src/types/api.d.ts (자동 생성 - 직접 수정 금지)

export interface paths {
  "/api/image-processing": {
    get: operations["get_saved_images_api_image_processing_get"];
    post: operations["img_processing_api_image_processing_post"];
  };
  "/api/image-processing/save": {
    post: operations["img_processing_save_api_image_processing_save_post"];
  };
}

export interface components {
  schemas: {
    FileSaveResponse: {
      id: string;
      originNm: string;
      nm: string;
      path: string;
      mimeType: string;
      sizeBytes: number;
      uploadedAt: string;
      options: { [key: string]: string };
    };
    FileListResponse: {
      items: components["schemas"]["FileListItem"][];
      hasMore: boolean;
      nextCursorUploadedAt: string | null;
      nextCursorId: string | null;
    };
    // ... 기타 스키마
  };
}
```

---

## 생성된 타입 사용 방법

```typescript
// src/apis/imgPrcApi.ts
import type { components } from 'src/types/api.d';

// 응답 타입
type FileSaveResponse = components['schemas']['FileSaveResponse'];
type FileListResponse = components['schemas']['FileListResponse'];

// 요청 바디 타입
type ImgProcessingBody =
  components['schemas']['Body_img_processing_api_image_processing_post'];

// PrcType 추출 (Literal이라 인라인으로 생성됨)
type PrcType = ImgProcessingBody['prcType'];
// → "sobel" | "prewitt" | "laplacian" | ...
```

---

## PrcType 스키마 노트

현재 백엔드에서 `PrcType = Literal[...]`로 정의되어 있어,
OpenAPI에서 **독립 스키마**가 아닌 **인라인 enum**으로 표현된다.

| 방식 | OpenAPI 표현 | TS 접근 방법 |
|------|-------------|-------------|
| `Literal` (현재) | 인라인 enum | `ImgProcessingBody['prcType']` |
| `class PrcType(str, Enum)` | 독립 `$ref` | `components['schemas']['PrcType']` |

독립 스키마로 만들려면 백엔드에서 `Literal` → `Enum` 클래스로 변경 필요.

---

## 스키마 동기화 워크플로우

백엔드 스키마 변경 시:

```
1. FastAPI 라우터/스키마 수정
2. 서버 재시작
3. pnpm gen:types  ← 한 번만 실행
4. 타입 오류 확인 후 프론트엔드 코드 수정
```
