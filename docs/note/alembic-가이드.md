# Alembic DB 마이그레이션 가이드

## 1. Alembic이란

**DB 스키마 변경을 버전 관리**하는 Python 마이그레이션 도구.
DDL 변경사항을 파일로 관리하여, 어떤 환경에서든 동일한 DB 상태를 재현할 수 있다.

```
기존 방식: init.sql을 수동 실행, 변경 시 ALTER 문 직접 실행
Alembic:   마이그레이션 파일로 관리, 변경분만 자동 실행
```


## 2. 프로젝트 구조

```
fastapi-server/
├── alembic.ini                    ← 설정 파일 (DB URL, 로깅 등)
├── alembic/
│   ├── env.py                     ← 실행 환경 설정 (DB 연결 방법)
│   ├── script.py.mako             ← 마이그레이션 파일 템플릿
│   └── versions/                  ← 마이그레이션 파일들 (시간순)
│       ├── 6a62e70c10c5_init_schema.py        ← 최초 DDL
│       ├── a1b2c3d4e5f6_add_column_xxx.py     ← 컬럼 추가
│       └── ...
```


## 3. 핵심 개념

### 마이그레이션 파일

각 파일은 **upgrade(적용)**과 **downgrade(롤백)** 함수를 갖는다.

```python
revision = 'a1b2c3d4e5f6'        # 이 파일의 고유 ID
down_revision = '6a62e70c10c5'    # 이전 마이그레이션 ID (체인 연결)

def upgrade():
    op.execute("ALTER TABLE t_file ADD COLUMN tags text[]")

def downgrade():
    op.execute("ALTER TABLE t_file DROP COLUMN tags")
```

### 버전 체인

마이그레이션은 **체인 구조**로 순서대로 연결된다.

```
None → 6a62e70c10c5 (init) → a1b2c3d4 (add column) → b5c6d7e8 (alter table)
                                                                    ↑ head
```

### alembic_version 테이블

Alembic은 DB에 `alembic_version` 테이블을 자동 생성하여 **현재 적용된 버전**을 추적한다.

```sql
SELECT * FROM alembic_version;
-- version_num: '6a62e70c10c5'  ← 현재 이 버전까지 적용됨
```


## 4. 셋업 방법

### 4-1. 설치

```bash
pip install alembic
```

### 4-2. 초기화

```bash
alembic init alembic
```

생성되는 파일:
- `alembic.ini` — 설정 파일
- `alembic/env.py` — DB 연결 설정
- `alembic/versions/` — 마이그레이션 파일 디렉토리

### 4-3. env.py 설정

앱의 DB 설정을 Alembic에 연결한다.

```python
# alembic/env.py
from app.core.config import settings

# psycopg 드라이버 지정
db_url = settings.database_url.replace("postgresql://", "postgresql+psycopg://")
config.set_main_option("sqlalchemy.url", db_url)
```

이렇게 하면 `alembic.ini`에 DB URL을 하드코딩하지 않아도 된다.

### 4-4. 기존 DB가 있는 경우

이미 테이블이 있는 DB에 Alembic을 도입할 때는 **stamp**으로 현재 상태를 기록한다.

```bash
# 1. 현재 DDL을 마이그레이션 파일로 작성
alembic revision -m "init schema"
# → versions/에 파일 생성 → upgrade()에 DDL 작성

# 2. 기존 DB에 "이미 적용 완료"로 표시 (실제 DDL 실행 X)
alembic stamp head
```

**주의**: `stamp`은 마이그레이션을 실행하지 않고 버전만 기록한다.
이미 테이블이 있는 DB에서 `upgrade`를 실행하면 "이미 존재" 에러가 발생하므로 `stamp`을 써야 한다.


## 5. 사용법

### 새 마이그레이션 생성

```bash
alembic revision -m "add tags column to t_file"
```

생성된 파일을 열어서 upgrade/downgrade를 작성한다.

### 마이그레이션 적용

```bash
# 최신 버전까지 모두 적용
alembic upgrade head

# 한 단계만 적용
alembic upgrade +1
```

### 롤백

```bash
# 한 단계 롤백
alembic downgrade -1

# 특정 버전으로 롤백
alembic downgrade 6a62e70c10c5

# 전부 롤백 (주의!)
alembic downgrade base
```

### 상태 확인

```bash
# 현재 DB에 적용된 버전
alembic current

# 마이그레이션 히스토리
alembic history

# 적용 안 된 마이그레이션 확인
alembic heads
```


## 6. 마이그레이션 작성 패턴

### 컬럼 추가

```python
def upgrade():
    op.execute("ALTER TABLE t_file ADD COLUMN tags text[]")

def downgrade():
    op.execute("ALTER TABLE t_file DROP COLUMN tags")
```

### 테이블 생성

```python
def upgrade():
    op.execute("""
        CREATE TABLE t_new_table (
            id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY,
            name text NOT NULL
        )
    """)

def downgrade():
    op.execute("DROP TABLE IF EXISTS t_new_table")
```

### 인덱스 추가

```python
def upgrade():
    op.execute("CREATE INDEX ix_t_file_mime_type ON t_file (mime_type)")

def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_t_file_mime_type")
```

### 데이터 마이그레이션 (DML)

```python
def upgrade():
    op.execute("ALTER TABLE t_preset ADD COLUMN category text DEFAULT 'general'")
    op.execute("UPDATE t_preset SET category = 'system' WHERE is_system = true")

def downgrade():
    op.execute("ALTER TABLE t_preset DROP COLUMN category")
```


## 7. Docker에서의 동작

### Dockerfile

```dockerfile
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
```

컨테이너 시작 시 자동으로 마이그레이션을 실행한 뒤 서버를 시작한다.

### 동작 흐름

```
컨테이너 시작
  │
  ├── 최초 설치 (alembic_version 없음)
  │   → 전체 마이그레이션 순차 실행 (init → ... → head)
  │
  ├── 업데이트 (alembic_version 있음)
  │   → 변경분만 실행 (current → head)
  │
  └── 변경 없음 (이미 head)
      → 아무것도 실행 안 함 → 서버 바로 시작
```

### 배포 시 전달할 파일

```
docker-compose.prod.yaml   ← 이것만 있으면 됨
```

마이그레이션 파일은 backend 이미지에 포함되어 있으므로 별도 전달 불필요.


## 8. 주의사항

### downgrade는 반드시 작성할 것

롤백이 필요한 상황에 대비하여 downgrade를 항상 작성한다.

### 운영 DB에서 downgrade는 신중하게

데이터가 있는 운영 환경에서 컬럼/테이블 삭제는 **데이터 유실**을 초래한다.
롤백이 필요하면 데이터 백업 후 진행한다.

### 마이그레이션 파일은 수정하지 말 것

이미 적용된 마이그레이션 파일을 수정하면 다른 환경과 불일치가 발생한다.
수정이 필요하면 **새 마이그레이션을 추가**한다.

### 팀 작업 시 충돌

여러 사람이 동시에 마이그레이션을 만들면 `down_revision` 충돌이 발생할 수 있다.
이 경우 `alembic merge`로 브랜치를 합친다.

```bash
alembic merge -m "merge migrations" revision_a revision_b
```


## 9. 명령어 요약

| 명령어 | 용도 |
|---|---|
| `alembic revision -m "설명"` | 새 마이그레이션 파일 생성 |
| `alembic upgrade head` | 최신 버전까지 적용 |
| `alembic upgrade +1` | 한 단계 적용 |
| `alembic downgrade -1` | 한 단계 롤백 |
| `alembic downgrade base` | 전부 롤백 |
| `alembic current` | 현재 적용된 버전 확인 |
| `alembic history` | 마이그레이션 히스토리 |
| `alembic stamp head` | 현재 DB를 최신으로 표시 (실행 X) |
| `alembic merge -m "msg" a b` | 브랜치 합치기 |
