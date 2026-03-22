# Docker 배포 가이드

## 1. 전체 구조

```
개발 환경 (로컬)
├── fastapi-server/
│   ├── Dockerfile                          ← 백엔드 이미지 빌드
│   ├── docker-compose.yaml                 ← 개발용 (build로 로컬 빌드)
│   ├── docker-compose.prod.yaml            ← 배포용 (ghcr.io 이미지 참조)
│   ├── sql/init.sql                        ← DB 초기화 DDL
│   └── .github/workflows/docker-publish.yml
│
└── quasar-image-processing/
    ├── Dockerfile                          ← 프론트엔드 이미지 빌드 (멀티스테이지)
    ├── docker/nginx.conf                   ← nginx 프록시 설정
    ├── .dockerignore
    └── .github/workflows/docker-publish.yml
```


## 2. 컨테이너 구성

```
브라우저 → :80(또는 :3000) nginx (프론트엔드)
               ├── /          → SPA 정적 파일 서빙
               ├── /api/*     → 프록시 → :8000 백엔드
               └── /uploads/* → 프록시 → :8000 백엔드
                                    │
                                    └── :5432 PostgreSQL (DB)
```

| 서비스 | 이미지 | 포트 | 역할 |
|---|---|---|---|
| db | postgres:17 | 5432 | PostgreSQL 데이터베이스 |
| backend | fastapi-backend | 8000 | FastAPI + uvicorn |
| frontend | quasar-frontend | 80 | nginx + SPA 정적 파일 + API 프록시 |


### API_HOST 환경변수

```ts
// src/boot/axios.ts
export const API_HOST = import.meta.env.VITE_API_HOST ?? 'http://127.0.0.1:8000';
```

| 환경 | VITE_API_HOST | 동작 |
|---|---|---|
| 로컬 개발 | 미설정 → `http://127.0.0.1:8000` | 직접 백엔드 호출 |
| Docker | 빈 문자열 `""` | 상대 경로 → nginx 프록시 |

### DB 초기화 — `sql/init.sql`

PostgreSQL 컨테이너는 최초 실행 시 `/docker-entrypoint-initdb.d/` 내 SQL을 자동 실행

```yaml
volumes:
  - ./sql/init.sql:/docker-entrypoint-initdb.d/init.sql
```

## 5. 실행 방법

### 개발용 (로컬 빌드)

```bash
cd fastapi-server
docker compose up -d --build
```

### 배포용 (ghcr.io 이미지)

```bash
# 설치 대상에 전달할 파일: docker-compose.prod.yaml + sql/init.sql

docker login ghcr.io -u banhyungil
docker compose -f docker-compose.prod.yaml up -d
```


## 6. CI/CD — GitHub Actions

각 리포에 `.github/workflows/docker-publish.yml` 배치

### 트리거

```bash
git tag v1.0.0
git push origin v1.0.0   # → GitHub Actions 자동 실행
```

### 흐름

```
태그 푸시 → GitHub VM → 소스 체크아웃 → ghcr.io 로그인 → Docker 빌드 → 이미지 푸시
```

### 결과 이미지

| 리포 | 이미지 |
|---|---|
| fastapi-server | `ghcr.io/banhyungil/fastapi-backend:1.0.0` |
| quasar-image-processing | `ghcr.io/banhyungil/quasar-frontend:1.0.0` |

- `secrets.GITHUB_TOKEN`은 GitHub이 자동 제공하므로 별도 설정 불필요
- 태그 없이 일반 push로는 실행되지 않음


## 7. 이슈 & 해결

### 이슈 1: `quasar prepare` 실패

```
Error: This command must be executed inside a Quasar project folder.
```

**원인**: Dockerfile에서 `COPY package*.json` → `npm ci` 순서로 했는데, `npm ci`의 `postinstall`에서 `quasar prepare`가 실행됨. 이 시점에 `quasar.config.ts`가 아직 복사되지 않아 실패.

**해결**: `COPY . .`를 `npm ci` 이전으로 이동

```dockerfile
COPY . .       # 소스 전체 복사 먼저
RUN npm ci     # postinstall에서 quasar.config.ts 접근 가능
```

### 이슈 2: pyvips 빌드 실패

```
error: legacy-install-failure → pyvips
```

**원인**: `python:3.10-slim`에 C 컴파일러와 pkg-config가 없어서 pyvips 네이티브 빌드 실패

**해결**: `build-essential`, `pkg-config` 추가

```dockerfile
RUN apt-get install -y --no-install-recommends \
    libvips-dev build-essential pkg-config
```

### 이슈 3: `NotRequired` import 에러

```
ImportError: cannot import name 'NotRequired' from 'typing'
```

**원인**: `NotRequired`는 Python 3.11부터 지원. Dockerfile이 `python:3.10-slim` 사용 중

**해결**: `FROM python:3.11-slim`으로 변경

### 이슈 4: PostgreSQL 18 볼륨 호환 에러

```
Error: in 18+, these Docker images are configured to store database data in a format which is compatible with "pg_ctlcluster"
```

**원인**: `postgres:latest`가 18로 올라가면서 데이터 디렉토리 구조 변경. 기존 17 형식 볼륨과 호환 안 됨

**해결**:
1. 버전 고정: `image: postgres:17`
2. 기존 볼륨 삭제: `docker compose down -v`

### 이슈 5: 포트 충돌

```
Bind for 0.0.0.0:5434 failed: port is already allocated
Bind for 0.0.0.0:80 failed: port is already allocated
```

**원인**: 로컬에서 기존 DB 컨테이너(5434)와 Java 프로세스(80)가 이미 해당 포트 사용 중

**해결**: docker-compose에서 포트 변경
- DB: `5432:5432` (또는 충돌 안 하는 포트)
- Frontend: `3000:80`

포트 점유 확인 명령: `netstat -ano | grep ":80 "`

### 이슈 6: DB 테이블 미존재

```
psycopg.errors.UndefinedTable: relation "t_image_process" does not exist
```

**원인**: `docker compose down -v`로 볼륨 삭제 후 재시작하면 빈 DB 상태

**해결**: `sql/init.sql`에 DDL 추출 후 컨테이너 초기화 시 자동 실행되도록 마운트

```yaml
volumes:
  - ./sql/init.sql:/docker-entrypoint-initdb.d/init.sql
```

### 이슈 7: OSD 뷰어 버튼 이미지 누락

```
prefixUrl: '/node_modules/openseadragon/build/openseadragon/images/'
```

**원인**: Docker 빌드 후 node_modules가 없어서 OpenSeadragon 버튼 이미지 로드 실패

**해결**: OSD 기본 이미지 버튼을 제거하고 Quasar `q-btn`으로 대체

```ts
showNavigationControl: false  // OSD 기본 버튼 끄기
```

앱 디자인과 통일된 커스텀 버튼(확대/축소/홈/전체화면)으로 교체


## 8. .dockerignore

빌드 컨텍스트에서 불필요한 파일 제외 → 빌드 속도 향상 + 이미지 경량화

### 프론트엔드

```
node_modules, dist, .quasar, test-results, e2e, tests
```

### 백엔드

```
__pycache__, .pytest_cache, uploads, .env*, .venv, dockers
```
