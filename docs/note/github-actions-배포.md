# GitHub Actions & Container Registry 배포 가이드

## 1. GitHub Actions란

GitHub 리포지토리에서 **이벤트(push, PR, tag 등) 발생 시 자동으로 작업을 실행**하는 CI/CD 도구.
GitHub이 제공하는 가상머신(Ubuntu/Windows/macOS)에서 실행되며, 별도 서버 불필요.


## 2. 핵심 개념

### 워크플로우 구조

```
.github/workflows/docker-publish.yml   ← 이 위치에 있어야 GitHub이 인식

워크플로우 (Workflow)
  └── 이벤트 (on)           ← 언제 실행? (push, tag, PR 등)
  └── 잡 (jobs)             ← 무엇을 실행?
       └── 실행환경 (runs-on) ← 어디서? (ubuntu-latest 등)
       └── 스텝 (steps)      ← 순서대로 실행할 단계들
            └── uses          ← 미리 만들어진 액션 사용
            └── run           ← 직접 명령어 실행
```

### 주요 용어

| 용어 | 설명 |
|---|---|
| **Workflow** | `.yml` 파일 하나 = 하나의 자동화 파이프라인 |
| **Event (on)** | 트리거 조건 (push, tag, schedule 등) |
| **Job** | 독립적인 실행 단위, 별도 VM에서 실행 |
| **Step** | Job 안의 개별 단계, 순차 실행 |
| **Action** | 재사용 가능한 단계 (`uses: actions/checkout@v4` 등) |
| **Secret** | 암호화된 환경변수 (`secrets.GITHUB_TOKEN` 등) |

### 트리거 예시

```yaml
# 태그 푸시 시
on:
  push:
    tags: ['v*']

# main 브랜치에 push 시
on:
  push:
    branches: [main]

# PR 생성 시
on:
  pull_request:
    branches: [main]

# 수동 실행
on:
  workflow_dispatch:

# 스케줄 (매일 자정)
on:
  schedule:
    - cron: '0 0 * * *'
```


## 3. GitHub Container Registry (ghcr.io)

GitHub이 제공하는 **Docker 이미지 저장소**.
GitHub 계정만 있으면 바로 사용 가능.

### Docker Hub와 비교

| | Docker Hub (무료) | ghcr.io |
|---|---|---|
| 비공개 저장소 | 1개 | 무제한 |
| Pull 제한 | 6시간당 200회 | 없음 |
| GitHub 연동 | 별도 설정 | 자동 (GITHUB_TOKEN) |
| 이미지 주소 | `docker.io/user/image` | `ghcr.io/user/image` |

### 이미지 주소 형식

```
ghcr.io/{GitHub사용자명}/{이미지이름}:{태그}

예: ghcr.io/banhyungil/fastapi-backend:1.0.0
    ghcr.io/banhyungil/quasar-frontend:latest
```


## 4. 사용 방법

### 4-1. 이미지 빌드 & 푸시 (개발자)

```bash
# 1. 코드 작업 완료 & 푸시
git add .
git commit -m "v1.0.0 릴리스"
git push origin main

# 2. 태그 생성 & 푸시 → GitHub Actions 자동 실행
git tag v1.0.0
git push origin v1.0.0
```

### 4-2. 빌드 상태 확인

GitHub 리포 → **Actions** 탭에서 실행 상태 확인 가능
- 초록색: 성공
- 빨간색: 실패 (로그 확인 가능)

### 4-3. 빌드된 이미지 확인

GitHub 리포 → **Packages** 탭에서 이미지 목록 확인


## 5. 설치 대상에서 이미지 사용

### 5-1. ghcr.io에서 pull (인터넷 가능 시)

```bash
# 로그인
docker login ghcr.io -u banhyungil

# docker-compose.prod.yaml로 실행
docker compose -f docker-compose.prod.yaml up -d
```

`docker-compose.prod.yaml`에서 `image: ghcr.io/...`로 참조하므로 자동으로 pull됨.

### 5-2. 오프라인 설치 (인터넷 불가 시)

```bash
# 개발 PC에서 이미지를 파일로 저장
docker pull ghcr.io/banhyungil/fastapi-backend:1.0.0
docker pull ghcr.io/banhyungil/quasar-frontend:1.0.0
docker save ghcr.io/banhyungil/fastapi-backend:1.0.0 \
            ghcr.io/banhyungil/quasar-frontend:1.0.0 \
            postgres:17 | gzip > app-images.tar.gz

# 설치 대상에 전달할 파일
#   app-images.tar.gz
#   docker-compose.prod.yaml
#   sql/init.sql

# 설치 대상에서 이미지 로드 & 실행
docker load < app-images.tar.gz
docker compose -f docker-compose.prod.yaml up -d
```


## 7. 태그 관리

### 태그 목록 확인

```bash
git tag           # 로컬 태그 목록
git ls-remote --tags origin   # 원격 태그 목록
```

### 태그 삭제

```bash
# 로컬 삭제
git tag -d v1.0.0

# 원격 삭제
git push origin --delete v1.0.0
```

### 버전 규칙 (Semantic Versioning)

```
v{MAJOR}.{MINOR}.{PATCH}

MAJOR: 호환 안 되는 변경 (v2.0.0)
MINOR: 기능 추가 (v1.1.0)
PATCH: 버그 수정 (v1.0.1)
```


## 8. 비공개 이미지 설정

ghcr.io에 올라간 이미지는 기본적으로 **비공개**.
공개로 변경하려면:

GitHub → Packages → 해당 이미지 → Package settings → Danger Zone → Change visibility


## 9. 흐름 요약

```
개발자                          GitHub                      설치 대상
  │                               │                            │
  │  git tag v1.0.0               │                            │
  │  git push origin v1.0.0       │                            │
  │ ─────────────────────────────>│                            │
  │                               │  Actions 실행              │
  │                               │  Docker 빌드               │
  │                               │  ghcr.io 푸시              │
  │                               │ ──────────────────────────>│
  │                               │                            │  docker compose up
  │                               │                            │  이미지 pull
  │                               │                            │  서비스 실행
```
