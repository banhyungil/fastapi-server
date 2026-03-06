# 코딩 컨벤션

- 파일/변수: `snake_case`, 클래스: `PascalCase`, 상수: `UPPER_SNAKE_CASE`
- import: 절대경로 (`app.xxx`), 와일드카드 금지
- 응답 모델: dict 대신 Pydantic 모델 사용
- 엔드포인트는 얇게 유지 (비즈니스 로직은 service로 위임)
- 타입힌트 필수 (public 함수)
- DB: psycopg3 context manager + parameterized query (SQL injection 방지)
