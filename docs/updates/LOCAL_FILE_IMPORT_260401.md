## LOCAL_FILE_IMPORT_260401:15

- `t_file`에 `source_type` 컬럼 추가 (upload/local 구분)
- `uq_t_file_local_path` 부분 유니크 인덱스 추가 (source_type='local' 조건)
- `POST /api/files/local/scan` — 디렉토리 스캔하여 이미지 파일 목록 반환
- `POST /api/files/local/register` — 선택한 로컬 파일을 DB에 등록 (원본 경로 참조)
- `delete_file()` — source_type='local'이면 디스크 파일 삭제 건너뛰기
- 기존 repo/schema에 source_type 필드 반영
- 새 파일: `files_local_schema.py`, `files_local_service.py`, `files_local.py` (endpoint)
