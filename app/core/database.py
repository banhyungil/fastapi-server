from alembic import command
from alembic.config import Config

from psycopg_pool import ConnectionPool
from app.core.config import settings
from psycopg import Cursor
import logging

# sqlLogger
sqlLogger = logging.getLogger("sql")

# pycopg의 Cursor를 상속하여 SQL 쿼리와 파라미터를 로그로 출력하는 LoggingCursor 클래스 정의
class LoggingCursor(Cursor):
    def execute(self, query, params=None, **kwargs):
        sqlLogger.debug("SQL: %s | params: %s", query, params)
        return super().execute(query, params, **kwargs)

# ConnectionPool 생성, cursor_factory에 LoggingCursor 설정하여 쿼리 로깅
## max_size 산정식: max_size = CPU 코어 수 * 2 + 디스크 수
pool = ConnectionPool(settings.database_url, open=False, max_size=9, kwargs={"cursor_factory": LoggingCursor})

def run_migrations() -> None:
    """alembic을 사용하여 데이터베이스 마이그레이션 실행"""

    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")