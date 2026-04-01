"""add source_type column to t_file

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-04-01 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE public.t_file
        ADD COLUMN source_type varchar(10) DEFAULT 'upload' NOT NULL
    """)
    op.execute("COMMENT ON COLUMN public.t_file.source_type IS '파일 소스 유형 (upload: 웹 업로드, local: 로컬 참조)'")

    # 로컬 파일 경로 중복 방지 (source_type = 'local'인 경우만)
    op.execute("""
        CREATE UNIQUE INDEX uq_t_file_local_path
        ON public.t_file (path)
        WHERE source_type = 'local'
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS public.uq_t_file_local_path")
    op.execute("ALTER TABLE public.t_file DROP COLUMN IF EXISTS source_type")
