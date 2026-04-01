## UUID_TO_SEQUENCE_260401:12

- 전체 테이블(6개) PK를 uuid → bigserial로 전환
- pgcrypto extension 제거
- Repos: `::uuid` 캐스팅, `::text` 변환 제거
- Schemas: ID 필드 `str` → `int` 타입 변경, "(UUID)" description 제거
- Services/Endpoints: UUID 타입 힌트 → int로 변경, 캐시 경로용 `str()` 변환 추가
- 테스트: mock ID를 문자열에서 정수로 변경
- 프론트엔드: 타입 파일 4개의 ID 필드 `string` → `number`
- `uuid4().hex`(파일명 생성), `crop_id`(캐시 파일명)는 DB PK와 무관하여 유지
