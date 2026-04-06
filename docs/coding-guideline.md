# 코딩 컨벤션

- 파일/변수: `snake_case`, 클래스: `PascalCase`, 상수: `UPPER_SNAKE_CASE`
- import: 절대경로 (`app.xxx`), 와일드카드 금지
- 라우터에서 서비스 import: 모듈 alias 사용 — `from app.services import xxx_service as svc`
  - 라우터와 대응하는 service의 경우는 `svc` alias 사용
  - 그외 service 사용시에는 `<약어>Svc` alias 사용
  - `app.services.modules`는 파일 이름을 모듈 alias로 사용 하되 긴 경우 약어 허용
- 응답 모델: dict 대신 Pydantic 모델 사용
- 엔드포인트는 얇게 유지 (비즈니스 로직은 service로 위임)
- 타입힌트 필수 (public 함수)
- DB: psycopg3 context manager + parameterized query (SQL injection 방지)

# 리소스 기반 구조화

- 리소스 기반 경로 — 동사(image-processing) → 명사(/files)
- 라우터-서비스-repo 1:1 매칭 — 파일명 통일 (files.py → files_service.py → files_repo.py)
- 서비스 디렉토리 구조:
  - `services/` 루트 — 라우터 대응 서비스 (`_service` suffix, e.g. `files_service.py`)
  - `services/modules/` — 내부 보조 모듈 (e.g. `crop.py`, `dzi.py`, `thumbnails.py`, `operations.py`, `cache.py`)
    `utils` 성격과는 다름. 비즈니스 로직 관련 기능
- Schemas 1:1 매칭 (files_schema.py), resource가 아닌 경우도 schema postfix 사용
- 복수형 통일 — 리소스는 복수형 (files, filters, presets, processes)
- 역할별 세그먼트 — /files/crop, /files/process, /files/dzi 처럼 동작을 하위 경로로
- 프론트-백엔드 네이밍 일치 — 백엔드 /files/crop → 프론트 filesApi.createCrop

# 라우터 함수 네이밍

- 리소스 단수형 사용 — `custom_filter`, `file`, `preset`
- `_endpoint` suffix 사용하지 않음
- 서비스 함수와 이름 충돌 시 모듈 alias import 사용 — `from app.services import xxx_service as svc`
- CRUD 네이밍 패턴:
  - 목록 조회: `list_{resource}` (e.g. `list_custom_filter`)
  - 단건 조회: `get_{resource}` (e.g. `get_custom_filter`)
  - 생성: `create_{resource}` (e.g. `create_custom_filter`)
  - 수정: `update_{resource}` (e.g. `update_custom_filter`)
  - 삭제: `delete_{resource}` (e.g. `delete_custom_filter`)
- 비 CRUD 동작: `{action}_{resource}` (e.g. `test_custom_filter`, `preview_custom_filter`)
