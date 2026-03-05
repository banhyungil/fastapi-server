# Python 타입 관리 방안

FastAPI + Pydantic 환경에서 자주 사용하는 타입 정의 패턴 정리.

---

## 1. Literal — 허용 값 열거

```python
from typing import Literal

PrcType = Literal["sobel", "prewitt", "laplacian", ...]
```

- 특정 문자열/값만 허용할 때 사용
- 타입체커가 잘못된 값 즉시 감지
- FastAPI Form/Query 파라미터에 사용 시 **자동 enum 검증** (422 자동 반환)
- **단점**: OpenAPI에 독립 스키마 아닌 인라인 enum으로 노출됨
  - 독립 스키마로 만들려면 `class PrcType(str, Enum)` 사용

---

## 2. TypedDict — 고정 키 dict

```python
from typing import TypedDict, Required

# 모든 키 필수
class Options(TypedDict):
    prc_type: str
    kernel_size: int

# 일부 키만 필수 (Python 3.11+)
class Options(TypedDict, total=False):   
    prc_type: Required[str]   # 필수
    kernel_size: int          # 선택
```

- 순수 dict 타입을 명시적으로 표현할 때 사용
- 런타임에는 일반 dict와 동일 (오버헤드 없음)
- **단점**: 가변 추가 키를 타입으로 표현하기 어려움 (Python 3.13 이전)
- Pydantic 직렬화/검증 불필요할 때 적합

---

## 3. Pydantic BaseModel — 구조화 모델

```python
from pydantic import BaseModel, ConfigDict

class MyModel(BaseModel):
    name: str
    age: int
```

- 입력 **검증 + 직렬화** 자동 처리
- FastAPI request/response body에 사용
- OpenAPI 스키마에 **독립 컴포넌트**로 노출됨

### 3-1. CamelCase 자동 변환

```python
def to_camel(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)

class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,   # snake_case → camelCase 자동 변환
        populate_by_name=True,      # snake_case로도 값 설정 가능
    )
```

### 3-2. model_config 상속

Pydantic v2는 자식 클래스에서 `model_config`를 정의하면 **부모 설정과 병합**된다.
명시한 키만 오버라이드되고, 나머지는 부모 값을 유지.

```python
class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

class FileSaveOptions(CamelModel):
    model_config = ConfigDict(extra="allow")  # extra만 추가
    # 실제 적용: alias_generator + populate_by_name + extra="allow"
```

### 3-3. 가변 추가 키 허용

```python
class FileSaveOptions(CamelModel):
    model_config = ConfigDict(extra="allow")
    prc_type: PrcType   # 필수 고정 속성
    # 그 외 키는 런타임에 자유롭게 추가 가능
```

---

## 4. Enum — 독립 스키마로 노출

```python
from enum import Enum

class PrcType(str, Enum):
    sobel = "sobel"
    prewitt = "prewitt"
    ...
```

- `Literal`과 달리 OpenAPI에 **독립 스키마**로 노출됨
  → `components['schemas']['PrcType']` 으로 TS 타입 접근 가능
- 값 비교 시 `PrcType.sobel` 또는 `"sobel"` 둘 다 가능 (`str` 상속)
- **단점**: 정의가 verbose, 값 추가 시 두 곳(이름/값) 모두 수정 필요

---

## 5. Annotated — 타입에 메타데이터 부착

`Annotated[T, 메타데이터...]` 형식으로 타입 자체는 유지하면서 부가 정보를 붙인다.

```python
from typing import Annotated
```

### 5-1. FastAPI 파라미터 정의 (권장 패턴)

`Query`, `Path`, `Body`, `Form`, `File` 등을 `Annotated` 안에 넣으면 타입과 파라미터 설정을 분리할 수 있다.

```python
from fastapi import Query, Form, File, UploadFile

# Annotated 미사용 (구식)
def old(limit: int = Query(20, ge=1, le=100)): ...

# Annotated 사용 (권장)
def new(limit: Annotated[int, Query(ge=1, le=100)] = 20): ...
```

- 타입(`int`)과 FastAPI 설정(`Query`)이 분리되어 가독성 향상
- 기본값은 `Annotated` 바깥에 `= 20`으로 명시 (타입 정보와 혼재하지 않음)
- `File`, `Form`도 동일하게 적용:

```python
async def img_processing(
    file: Annotated[UploadFile, File()],
    form: Annotated[ImgProcessingForm, Form()],
): ...
```

### 5-2. 메타데이터 여러 개 동시 부착

```python
from pydantic import Field

# Query 설정 + Field 검증 동시 적용
limit: Annotated[int, Query(description="페이지 크기"), Field(ge=1, le=100)] = 20
```

### 5-3. 타입 별칭으로 재사용

```python
# 반복 사용하는 파라미터를 타입 별칭으로 추출
PageLimit = Annotated[int, Query(ge=1, le=100, description="페이지 크기")]

def list_images(limit: PageLimit = 20): ...
def list_files(limit: PageLimit = 50): ...
```

---

## 6. Doc — 파라미터 인라인 문서화

`typing_extensions.Doc`은 `Annotated` 안에서 파라미터/반환값에 설명을 붙이는 전용 클래스다 (PEP 727, Python 3.13+ stdlib 편입, 그 이전은 `typing_extensions` 사용).

```python
from typing import Annotated
from typing_extensions import Doc
```

### 6-1. 함수 파라미터 문서화

```python
def process_image(
    prc_type: Annotated[PrcType, Doc("적용할 이미지 처리 종류")],
    image_bytes: Annotated[bytes, Doc("원본 이미지 바이너리")],
    kernel_size: Annotated[int | None, Doc("커널 크기 (홀수). None이면 처리 종류별 기본값 사용")] = None,
) -> bytes:
    ...
```

### 6-2. FastAPI + Doc 조합

`Query`/`Form` 등과 함께 쓸 때 `description`과 `Doc` 중 하나만 사용한다. FastAPI 내부 소스에서는 `Doc`을 사용한다.

```python
async def get_saved_images(
    limit: Annotated[int, Query(ge=1, le=100), Doc("반환할 최대 항목 수")] = 20,
    cursor_uploaded_at: Annotated[
        datetime | None,
        Query(alias="cursorUploadedAt"),
        Doc("커서 기준 업로드 시각 (cursor_id와 함께 제공해야 함)"),
    ] = None,
): ...
```

### 6-3. Doc vs Query(description=...)

| | `Doc(...)` | `Query(description=...)` |
|---|---|---|
| 목적 | 소스코드 독자 대상 설명 | OpenAPI 문서(Swagger) 노출 |
| IDE 지원 | hover 시 표시됨 | 미지원 |
| 런타임 영향 | 없음 | OpenAPI 스키마에 반영 |

OpenAPI에도 설명을 노출하려면 `Query(description=...)` 또는 둘 다 사용.

---

## 7. Docstring — 함수/클래스 문서화

Python 표준 문서화 방식. IDE hover, `help()`, 문서 생성 도구가 읽는다.

### 7-1. 한 줄 docstring

```python
def to_camel(value: str) -> str:
    """snake_case 문자열을 camelCase로 변환한다."""
    ...
```

### 7-2. Google 스타일 (이 프로젝트 권장)

FastAPI/Pydantic 생태계에서 가장 보편적으로 사용되는 형식.

```python
def process_image(
    prc_type: PrcType,
    image_bytes: bytes,
    kernel_size: int | None = None,
) -> bytes:
    """이미지에 지정한 처리를 적용하고 PNG 바이너리를 반환한다.

    Args:
        prc_type: 적용할 처리 종류.
        image_bytes: 원본 이미지 바이너리.
        kernel_size: 커널 크기 (홀수). None이면 처리 종류별 기본값 사용.

    Returns:
        처리 결과 이미지의 PNG 인코딩 바이너리.

    Raises:
        ValueError: prc_type이 유효하지 않거나 kernel_size가 짝수인 경우.
        RuntimeError: OpenCV 처리 중 오류가 발생한 경우.
    """
    ...
```

### 7-3. 클래스 docstring

```python
class CamelModel(BaseModel):
    """응답 JSON을 camelCase로 자동 변환하는 Pydantic 베이스 모델.

    FastAPI 응답 모델의 베이스 클래스로 사용한다.
    snake_case Python 필드가 JSON 직렬화 시 camelCase로 변환된다.
    """
    ...
```

### 7-4. Docstring vs Annotated[..., Doc(...)]

| | Docstring | `Doc(...)` |
|---|---|---|
| 위치 | 함수/클래스 본문 첫 줄 | 타입 힌트 안 |
| 용도 | 함수 전체 설명, Args/Returns/Raises | 파라미터 하나의 설명 |
| 중복 여부 | 같이 써도 무방 | Docstring의 Args 항목 대체 가능 |

단순 함수는 docstring만으로 충분. 라이브러리처럼 API를 명시적으로 노출할 때 `Doc`을 추가.

---

## 선택 기준

| 상황 | 권장 |
|------|------|
| 허용 값 열거 (내부 검증용) | `Literal` |
| 허용 값 열거 (OpenAPI 독립 스키마 필요) | `Enum` |
| 단순 dict 구조 명세 | `TypedDict` |
| API 요청/응답 바디 | `BaseModel` |
| 고정 키 + 가변 추가 키 | `BaseModel` + `extra="allow"` |
| FastAPI 파라미터 설정 | `Annotated[T, Query(...)]` |
| 파라미터 인라인 설명 | `Annotated[T, Doc(...)]` |
| 함수/클래스 전체 설명 | Docstring (Google 스타일) |
