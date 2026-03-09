# FastAPI Server

초기 아키텍처가 적용된 FastAPI 프로젝트입니다.

## 시스템 요구사항
### libvips 설치
- https://github.com/libvips/build-win64-mxe/releases/tag/v8.18.0
- vips-dev-w64-web-8.18.0.zip 설치
- 압축해제 후 환경변수 등록


## 구조

```text
app/
  api/
    endpoints/
    router.py
  core/
    config.py
  schemas/
  main.py
```

## 시작하기

1. 가상환경 생성 및 활성화
2. 의존성 설치
- requirements.txt는 의존성 라이브러리 관리 역할 담당

```bash
pip install -r requirements.txt
```


3. 환경변수 파일 생성

```bash
copy .env.example .env
```

4. 서버 실행

```bash
uvicorn app.main:app --reload
```
- uvicorn: ASGI 서버 실행 명령
- app.main: 파이썬 모듈 경로 (main.py)
- :app: 그 모듈 안 변수 이름 app = FastAPI(...)
- --reload: hmr


```bash
# fastapi 전용
fastapi dev
```

## 엔드포인트

- `GET /` : 루트 확인
- `GET /docs` : Swagger UI

## 팀 표준(venv)

### 1. 최초 1회 설정

```bash
python -m venv .venv
```

PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Git Bash:

```bash
source .venv/Scripts/activate
```

의존성 설치:

```bash
pip install -r requirements.txt
```

### 2. VS Code 인터프리터 고정

- `Python: Select Interpreter`에서 `.venv/Scripts/python.exe` 선택
- 확인 명령:

```bash
python -c "import sys; print(sys.executable)"
```

### 3. 의존성 관리 원칙

- `.venv/`는 Git에 커밋하지 않음
- 새 패키지 설치 후 `requirements.txt`를 반드시 함께 업데이트
- 팀/CI는 `pip install -r requirements.txt`로 동일 환경 구성

### 4. 매일 개발 시작 루틴

```bash
# (프로젝트 루트)
source .venv/Scripts/activate   # PowerShell은 Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```


## 프로젝트 구조
### api

- api 용도에 필요한 파일들을 모아놓는다.
- endpoints 폴더 하위에 실제 router를 위치시킨다.

### core

- “핵심 공통 설정/인프라” 설정 
예: 설정값, 보안/인증 설정, 로깅 설정, 공통 예외 처리, 미들웨어 초기화.
순수 유틸 함수 모음은 보통 utils(또는 common)로 따로 분리하는 팀도 많습니다.

### schemas

- 데이터 모델 정의 용도
- 예들들어, 응답, 요청 데이터 모델을 정의해서 사용할 수 있다(선언적)
- ts type보다 범용적인 것은 class 형태라 검증 함수 같은 것도 추가하여 사용할 수 있다.

## Convention

### 1. 네이밍

- 파일/모듈: `snake_case.py`
- 함수/변수: `snake_case`
- 클래스(Pydantic 포함): `PascalCase`
- 상수: `UPPER_SNAKE_CASE`
- 내부 전용(비공개) 심볼: `_leading_underscore`

### 2. 코드 스타일

- PEP 8 준수 (들여쓰기 4칸, 의미 있는 변수명 사용)
- 한 줄 길이는 가능하면 88자 내외로 유지
- 중복 로직은 함수로 분리하고, 라우터 함수는 짧게 유지
- 주석은 "무엇"보다 "왜"를 설명할 때만 작성

### 3. 타입 힌트

- public 함수는 파라미터/리턴 타입 힌트를 명시
- 응답 모델은 `dict` 대신 Pydantic 스키마 사용을 우선
- `Any` 사용은 최소화하고 구체 타입 사용

### 4. Import 규칙

- 표준 라이브러리 → 서드파티 → 로컬 모듈 순서
- 와일드카드 import(`from x import *`) 금지
- 순환 참조가 생기지 않게 레이어 방향 유지

### 5. FastAPI 레이어 규칙

- `api/endpoints`: HTTP 입출력 처리(최대한 얇게 유지)
- `schemas`: 요청/응답 데이터 모델 정의
- `core`: 설정/보안/로깅 같은 앱 공통 인프라
- `api/router.py`: 라우터 조립(`include_router`) 전담

### 6. 에러/응답 처리

- 예상 가능한 비즈니스 오류는 `HTTPException`으로 명시
- 성공/실패 응답 포맷은 엔드포인트 간 일관성 유지
- 내부 예외 원문을 그대로 노출하지 않음

### 7. 환경변수/설정

- 코드에 민감정보 하드코딩 금지
- `.env`는 로컬 전용, 샘플은 `.env.example`에만 유지
- 설정값 접근은 `core/config.py`를 통해 일원화

### 8. 테스트/품질

- 최소 기준: 새 엔드포인트 추가 시 헬스체크 수준의 API 테스트 포함
- 린트/포맷터 도입 시 팀 규칙으로 고정 (`ruff`, `black` 권장)
- 리팩터링 시 동작 변경이 없으면 테스트 결과도 동일해야 함
