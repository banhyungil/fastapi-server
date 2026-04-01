# UUID → Sequence PK 전환 방안

## 배경

- 로컬 단독 사용 환경에서 UUID의 분산/보안 이점이 불필요
- Sequence가 인덱스 성능, 저장 공간, 가독성 면에서 유리
- 향후 신규 테이블도 Sequence로 통일

## 변경 범위

### 1. Alembic 마이그레이션 (신규 마이그레이션 파일 생성)

6개 테이블의 PK 및 FK를 `uuid` → `BIGSERIAL`/`BIGINT`로 변경:

| 테이블 | PK | FK (uuid → bigint) |
|--------|----|--------------------|
| `t_file` | `id` | `uploader_id` (제거 또는 유지) |
| `t_custom_filter` | `id` | - |
| `t_preset` | `id` | - |
| `t_preset_step` | `id` | `preset_id`, `parent_id` |
| `t_image_process` | `id` | `file_id`, `final_file_id` |
| `t_process_step` | `id` | `process_id`, `parent_id`, `preset_id` |

**마이그레이션 전략:** 기존 데이터가 중요하지 않으므로 전체 테이블 DROP → 재생성 (깔끔한 스키마)

- `gen_random_uuid()` DEFAULT 제거
- `pgcrypto` extension 불필요 시 제거
- `id::text` 캐스팅 → 불필요 (정수는 그대로 반환)
- `%s::uuid` 캐스팅 → 제거
- 커서 페이징: `(uploaded_at, id) < (%s, %s)` 에서 id 타입만 변경

### 2. Repos (4개 파일)

#### `files_repo.py`
- `from uuid import UUID` 제거
- `FileRowInput.uploader_id`: `UUID | None` → `int | None`
- `get_file_list()`: `cursor_id: UUID | None` → `int | None`
- SQL에서 `id::text`, `%s::uuid` 제거
- `FileRow.id`, `InsertedFileMeta.id`, `FileRowPage.next_cursor_id`: `str` → `int`

#### `processes_repo.py`
- 모든 `%s::uuid` 제거
- 모든 `id::text`, `file_id::text`, `process_id::text` 등 캐스팅 제거
- `_step_row_to_dict`, `_row_to_dict` 반환값은 그대로 (dict)

#### `presets_repo.py`
- 모든 `%s::uuid` 제거
- 모든 `id::text`, `parent_id::text` 캐스팅 제거

#### `custom_filters_repo.py`
- 모든 `%s::uuid` 제거
- `id::text` 캐스팅 제거

### 3. Schemas (5개 파일)

#### `file.py`
- `FileSaveResponse.id`, `TFile.id`, `FileUploadResponse.id`: `str` → `int`
- `FileListResponse.next_cursor_id`: `str | None` → `int | None`
- description에서 "(UUID)" 문구 제거
- `nm` 필드 description "UUID 기반" → "고유 파일명"

#### `process.py`
- `ProcessStepResponse.id`, `process_id`: `str` → `int`
- `ProcessStepBase.preset_id`, `parent_id`: `str | None` → `int | None`
- `ProcessCreate.file_id`: `str` → `int`
- `ProcessUpdate.final_file_id`: `str | None` → `int | None`
- `ProcessResponse.id`, `file_id`, `final_file_id`: `str` / `str | None` → `int` / `int | None`

#### `preset.py`
- `PresetStepResponse.id`: `str` → `int`
- `PresetStepResponse.parent_id`: `str | None` → `int | None`
- `PresetResponse.id`: `str` → `int`

#### `custom_filter.py`
- `CustomFilterResponse.id`: `str` → `int`
- description에서 "(UUID)" 제거

#### `image_processing.py`
- `filter_id` 필드가 있다면 description 수정

### 4. Services (2개 파일)

#### `files_service.py`
- `from uuid import UUID` 제거
- `list_files()`: `cursor_id: UUID | None` → `int | None`

#### `crop.py`
- `from uuid import uuid4` 제거
- `crop_id = uuid4().hex` → 다른 고유 ID 생성 방식 사용
  - 옵션: `secrets.token_hex(16)` 또는 타임스탬프 기반
  - crop_id는 DB PK가 아닌 캐시 파일명이므로 UUID 유지해도 무방

### 5. Endpoints (1개 파일)

#### `files.py`
- `from uuid import uuid4, UUID` → `from uuid import uuid4` (uuid4는 파일명 생성에 계속 사용)
- `cursor_id: Annotated[UUID | None, ...]` → `Annotated[int | None, ...]`
- 나머지 `file_id: str` 파라미터는 str 유지 (FastAPI path param은 str로 받아도 무방)
  - 또는 `file_id: int`로 변경하여 타입 안전성 확보

### 6. 프론트엔드 (quasar-image-processing)

ID를 현재 `string`으로 다루고 있으므로 **`string` 유지 가능** (정수도 JSON에서 문자열로 변환). 다만 타입을 명확히 하려면:

- `src/types/imgPrcType.ts`: `id: string` → `id: number`
- `src/types/processType.ts`: 각 ID 필드 `string` → `number`
- `src/types/presetType.ts`: 각 ID 필드 `string` → `number`
- `src/types/customFilterType.ts`: `id: string` → `id: number`
- `src/types/api.d.ts`: OpenAPI 스키마에서 자동 재생성
- API 호출부에서 ID를 `number`로 처리

## 변경하지 않는 것

- `uuid4().hex` — 파일명 생성용 (disk 저장 이름). DB PK와 무관
- `crop_id` — 캐시 파일명용. DB에 저장하지 않음
- `client_id`, `parent_client_id` — 프론트에서 보내는 임시 ID. DB PK와 무관

## 작업 순서

1. Alembic 마이그레이션 파일 작성 (DROP + CREATE)
2. Repos 수정 (uuid 캐스팅 제거)
3. Schemas 수정 (타입 변경)
4. Services 수정
5. Endpoints 수정
6. `npx pyright` 타입 검증
7. 테스트 실행
8. 프론트엔드 타입 수정

## 참고

- 기존 데이터는 마이그레이션 시 초기화됨 (개발 단계이므로 문제없음)
- `t_file.content_hash` 유니크 인덱스는 그대로 유지
- 커서 페이징 로직: `(uploaded_at DESC, id DESC)` — id가 정수로 바뀌어도 동일하게 동작
