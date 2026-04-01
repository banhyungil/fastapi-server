# 로컬 파일 가져오기 방안

## 개요

로컬 디렉토리를 탐색하여 이미지 파일을 선택하고, 원본 경로를 그대로 `t_file`에 등록하는 기능.

## 결정 사항

- 원본 경로 그대로 참조 (`uploads/`에 복사하지 않음)
- 삭제 시 DB 레코드만 제거, 원본 파일은 유지
- 디렉토리 경로 입력 → 이미지 목록 조회 → 체크박스로 선택 → 등록
- 업로드 파일과 로컬 파일 중복 허용 (같은 파일이 둘 다 존재 가능)

## DB 변경

`t_file`에 `source_type` 컬럼 추가:

```sql
ALTER TABLE t_file ADD COLUMN source_type VARCHAR(10) DEFAULT 'upload' NOT NULL;
COMMENT ON COLUMN t_file.source_type IS '파일 소스 유형 (upload: 웹 업로드, local: 로컬 참조)';
```

- `'upload'` — 기존 동작, `uploads/`에 복사된 파일
- `'local'` — 로컬 절대 경로 직접 참조

### 로컬 파일 중복 방지

- `path`에 유니크 제약 추가 (로컬 파일은 같은 경로 = 같은 파일)
- 단, 업로드 파일은 `content_hash`로 중복 방지하므로 path 유니크는 `source_type = 'local'`인 경우만 적용

```sql
CREATE UNIQUE INDEX uq_t_file_local_path ON t_file (path) WHERE source_type = 'local';
```

## 백엔드 변경

### 1. Alembic 마이그레이션

- `source_type` 컬럼 추가
- `uq_t_file_local_path` 부분 유니크 인덱스 추가

### 2. 새 API 엔드포인트

#### `POST /api/files/local/scan` — 디렉토리 스캔

요청:
```json
{
  "dirPath": "C:/images/samples",
  "recursive": false
}
```

응답:
```json
{
  "items": [
    {
      "path": "C:/images/samples/photo1.jpg",
      "fileName": "photo1.jpg",
      "mimeType": "image/jpeg",
      "sizeBytes": 204800,
      "width": 1920,
      "height": 1080,
      "alreadyRegistered": false
    }
  ]
}
```

처리:
- 지정 디렉토리에서 지원 확장자(png, jpg, webp, bmp, tiff) 필터링
- `recursive` 옵션에 따라 하위 디렉토리 포함 여부 결정
- 각 파일의 메타데이터(크기, 해상도) 추출
- `alreadyRegistered`: 해당 path가 이미 `t_file`에 존재하는지 체크

#### `POST /api/files/local/register` — 선택 파일 등록

요청:
```json
{
  "files": [
    { "path": "C:/images/samples/photo1.jpg" },
    { "path": "C:/images/samples/photo2.png" }
  ]
}
```

응답: `FileUploadResponse[]` (기존 업로드 응답과 동일 형태)

처리:
- 각 파일 존재 여부 확인
- MIME 타입 검증
- 이미지 해상도 추출
- `t_file` INSERT (`source_type = 'local'`, `nm = 파일명`, `path = 절대경로`)
- 이미 등록된 path는 건너뛰고 기존 레코드 반환
- 썸네일 생성

### 3. 기존 로직 수정

#### `files_service.py` — `delete_file()`

```python
# source_type이 'local'이면 디스크 파일 삭제 건너뛰기
if deleted.get("source_type") != "local":
    disk_path = Path(deleted["path"])
    if disk_path.exists():
        disk_path.unlink()
```

#### `files_repo.py`

- `FileRow`, `FileRowInput`에 `source_type` 필드 추가
- `insert_file_row()`에 `source_type` 파라미터 추가
- SELECT 쿼리에 `source_type` 컬럼 추가
- 로컬 파일 path 중복 조회 함수 추가: `find_local_by_path(path: str)`

#### `file.py` (schemas)

- `TFile`, `FileSaveResponse`, `FileUploadResponse`에 `source_type` 필드 추가

### 4. 새 파일

- `app/schemas/files_local_schema.py` — 스캔/등록 요청/응답 스키마
- `app/services/files_local_service.py` — 디렉토리 스캔 + 파일 등록 로직
- `app/api/endpoints/files_local.py` — `/files/local/*` 엔드포인트

> 기존 files 리소스의 하위 경로로 배치하되, 라우터 파일은 분리하여 코드 복잡도 관리

## 프론트엔드 변경

### 새 다이얼로그: `LocalImportDialog.vue`

1. 디렉토리 경로 입력 필드 + recursive 체크박스
2. "스캔" 버튼 → `POST /api/files/local/scan` 호출
3. 이미지 목록을 썸네일과 함께 표시 (이미 등록된 파일은 비활성화)
4. 체크박스로 선택 → "등록" 버튼 → `POST /api/files/local/register` 호출
5. 완료 후 갤러리 목록 새로고침

### 타입 추가

- `imgPrcType.ts`에 스캔/등록 관련 인터페이스 추가
- `TFile`에 `sourceType` 필드 추가

### API 함수 추가

- `filesApi.ts`에 `scanLocalDir()`, `registerLocalFiles()` 추가

## 작업 순서

1. Alembic 마이그레이션 (`source_type` 컬럼 + 인덱스)
2. 백엔드 기존 파일 수정 (repo, schema, service에 `source_type` 반영)
3. 백엔드 새 파일 생성 (schemas, service, endpoint)
4. 기존 `delete_file()` 로직 수정
5. pyright 타입 검증 + 테스트
6. 프론트엔드 구현

## 보안 고려

- 디렉토리 스캔은 로컬 전용이므로 경로 접근 제한 불필요
- 단, 심볼릭 링크 순환 방지를 위해 `os.scandir()` 사용 시 `follow_symlinks=False`
