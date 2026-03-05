# FastAPI Server - 프로젝트 가이드

## 프로젝트 개요

FastAPI 기반 이미지 처리 서버. OpenCV로 이미지 처리 후 결과를 반환하거나 PostgreSQL에 저장한다.

## 프로젝트 구조

```
fastapi-server/
├── app/
│   ├── main.py                              # FastAPI 앱 진입점, CORS/라우터/정적파일 설정
│   ├── api/
│   │   ├── router.py                        # 라우터 집합 
│   │   └── endpoints/
│   │       └── image_processing.py          # 엔드포인트
│   ├── core/
│   │   ├── config.py                        # Settings (BaseSettings, .env 로드)
│   │   └── exception_handlers.py            # 전역 예외 핸들러
│   ├── services/
│   ├── repos/
│   ├── schemas/
│   │   ├── file.py                          # 요청/응답 스키마, PrcType, CamelModel
│   └── utils/
│       └── timing.py                        # 실행시간 측정 데코레이터 (sync/async 지원)
├── uploads/                                 # 처리된 이미지 저장 디렉토리 (날짜별 하위폴더)
├── requirements.txt
└── .env.example
```

## 아키텍처

```
endpoints/ (HTTP 입출력)
    ↓
services/ (비즈니스 로직)
    ↓
repos/ (데이터 접근)
    ↓
PostgreSQL
```

**CamelModel**: 응답 JSON은 camelCase로 자동 변환 (Pydantic BaseModel 확장)

## 데이터베이스

- 커서 페이지네이션: `(uploaded_at DESC, id DESC)` 기준
- 드라이버: psycopg3 (binary), raw SQL

## 설정

```python
# app/core/config.py
```

## 개발 환경

- **런타임**: Python + FastAPI
- **패키지 관리**: pip (`requirements.txt`)
- **가상환경**: `.venv/`
- **DB**: PostgreSQL (localhost:5434)
- **정적파일**: `/uploads` → `uploads/` 디렉토리 마운트

## 코딩 컨벤션

- 파일/변수: `snake_case`, 클래스: `PascalCase`, 상수: `UPPER_SNAKE_CASE`
- import: 절대경로 (`app.xxx`), 와일드카드 금지
- 응답 모델: dict 대신 Pydantic 모델 사용
- 엔드포인트는 얇게 유지 (비즈니스 로직은 service로 위임)
- 타입힌트 필수 (public 함수)
