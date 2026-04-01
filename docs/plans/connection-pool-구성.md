# Connection Pool 구성 계획

## 현황

- 모든 repo 함수에서 `psycopg.connect()`를 개별 호출 (21곳)
- 매 요청마다 TCP 연결/해제 오버헤드 발생
- `psycopg[pool]` 설치 완료, `requirements.txt` 반영 완료

## 목표

- `ConnectionPool` 단일 인스턴스로 커넥션 관리 중앙화
- 서버 시작 시 pool open, 종료 시 pool close
- 각 repo에서 pool을 주입받아 사용

---

## 구현 단계

### 1. `app/core/database.py` 생성

```python
from psycopg_pool import ConnectionPool
from app.core.config import settings

pool = ConnectionPool(settings.database_url, open=False)
```

- `open=False`: lifespan에서 명시적으로 open

---

### 2. `app/main.py` lifespan에 pool 생명주기 추가

```python
from app.core.database import pool

@asynccontextmanager
async def lifespan(_app: FastAPI):
    run_migrations()
    pool.open()
    cleanup_cache()
    logger.info("cache cleanup completed on startup")

    async def _periodic_cleanup() -> None:
        while True:
            await asyncio.sleep(5 * 60)
            cleanup_cache()

    task = asyncio.create_task(_periodic_cleanup())
    yield
    task.cancel()
    pool.close()
```

---

### 3. 각 repo 수정 (4개 파일, 21곳)

| 파일                               | 변경 횟수 |
| ---------------------------------- | --------- |
| `app/repos/custom_filters_repo.py` | 5곳       |
| `app/repos/files_repo.py`          | 6곳       |
| `app/repos/presets_repo.py`        | 5곳       |
| `app/repos/processes_repo.py`      | 5곳       |

**변경 패턴:**

```python
# 기존
with pool.connection() as conn:

# 변경
from app.core.database import pool

with pool.connection() as conn:
```

- 각 파일 상단 `import psycopg` 및 `from app.core.config import settings` 제거
- `from app.core.database import pool` 추가

---

## 고려사항

- `pool.connection()`은 기존 `psycopg.connect()`와 동일하게 context manager로 동작 → 트랜잭션/커서 사용 코드 변경 불필요
- pool 기본 `min_size=4`, `max_size` 미지정 시 `min_size`와 동일 → 필요 시 `max_size` 조정
- 동기 코드이므로 `AsyncConnectionPool` 아닌 `ConnectionPool` 사용
