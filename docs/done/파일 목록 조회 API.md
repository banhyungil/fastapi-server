# 파일 목록 조회 API

## 개요

업로드된 파일을 MIME 타입 기준으로 필터링하여 조회하는 API.
기존 `GET /api/image-processing`은 처리 결과 파일 전용이므로, 범용 파일 조회를 위해 별도 라우터로 분리하였다.

## API

```
GET /api/files
```

### Query 파라미터

| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|:----:|------|
| `mimeType` | `string` | X | MIME 타입 필터. 정확 매칭(`image/png`) 또는 와일드카드(`image/*`) 지원 |
| `limit` | `int` | X | 반환 최대 항목 수 (1~100, 기본 20) |
| `cursorUploadedAt` | `datetime` | X | 커서 기준 업로드 시각 (`cursorId`와 함께 제공) |
| `cursorId` | `uuid` | X | 커서 기준 파일 ID (`cursorUploadedAt`와 함께 제공) |

### 응답 예시

```json
{
  "items": [
    {
      "id": "550e8400-...",
      "originNm": "photo.jpg",
      "nm": "abc123.jpg",
      "path": "uploads/2026-03-09/abc123.jpg",
      "mimeType": "image/jpeg",
      "sizeBytes": 204800,
      "uploadedAt": "2026-03-09T12:00:00Z",
      "options": {}
    }
  ],
  "hasMore": true,
  "nextCursorUploadedAt": "2026-03-09T12:00:00Z",
  "nextCursorId": "550e8400-..."
}
```

### 사용 예

```
# 이미지 파일만 조회
GET /api/files?mimeType=image/*

# PNG 파일만 조회
GET /api/files?mimeType=image/png

# 전체 파일 조회 (필터 없음)
GET /api/files

# 페이지네이션
GET /api/files?mimeType=image/*&limit=10&cursorUploadedAt=2026-03-09T12:00:00Z&cursorId=550e8400-...
```

## MIME 타입 필터 동작

| 입력 | SQL 조건 |
|------|---------|
| `image/png` | `mime_type = 'image/png'` |
| `image/*` | `mime_type LIKE 'image/%'` |
| 미지정 | 조건 없음 (전체 조회) |

## 변경 파일

| 파일 | 변경 내용 |
|------|-----------|
| `app/api/endpoints/file.py` | **신규** — `GET /api/files` 엔드포인트 |
| `app/api/endpoints/__init__.py` | `file_router` export 추가 |
| `app/api/router.py` | `file_router` 등록 |
| `app/repos/file_repo.py` | `get_file_list`에 `mime_type` 파라미터 추가 (WHERE 조건 동적 생성) |
| `app/services/file_service.py` | `list_files`에 `mime_type` 파라미터 전달 |
| `app/schemas/file.py` | `FileItem`, `FileItemListResponse` 스키마 추가 |
