"""add column comments

Revision ID: f00573979019
Revises: 6a62e70c10c5
Create Date: 2026-03-22 10:13:00.383535

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'f00573979019'
down_revision: Union[str, Sequence[str], None] = '6a62e70c10c5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -- t_custom_filter --
    op.execute("COMMENT ON COLUMN public.t_custom_filter.id IS '필터 고유 식별자 (UUID)'")
    op.execute("COMMENT ON COLUMN public.t_custom_filter.nm IS '필터 이름 (사용자 노출용)'")
    op.execute("COMMENT ON COLUMN public.t_custom_filter.description IS '필터 상세 설명'")
    op.execute("COMMENT ON COLUMN public.t_custom_filter.code IS '필터 파이썬 코드'")
    op.execute("COMMENT ON COLUMN public.t_custom_filter.params IS '필터 실행에 필요한 파라미터 정의 (JSON 형식)'")
    op.execute("COMMENT ON COLUMN public.t_custom_filter.version IS '필터 버전 관리 번호'")
    op.execute("COMMENT ON COLUMN public.t_custom_filter.created_at IS '데이터 생성 일시'")
    op.execute("COMMENT ON COLUMN public.t_custom_filter.updated_at IS '데이터 최종 수정 일시'")

    # -- t_file --
    op.execute("COMMENT ON COLUMN public.t_file.id IS '파일 고유 식별자 (UUID)'")
    op.execute("COMMENT ON COLUMN public.t_file.origin_nm IS '사용자가 업로드할 당시의 실제 파일명 (예: photo.jpg)'")
    op.execute("COMMENT ON COLUMN public.t_file.nm IS '서버 스토리지에 저장된 고유 파일명 (중복 방지용 UUID/타임스탬프 조합)'")
    op.execute("COMMENT ON COLUMN public.t_file.path IS '파일이 저장된 물리적 또는 클라우드 경로'")
    op.execute("COMMENT ON COLUMN public.t_file.mime_type IS '파일의 MIME 타입 (image/png, image/jpeg만 허용)'")
    op.execute("COMMENT ON COLUMN public.t_file.size_bytes IS '파일 크기 (바이트 단위)'")
    op.execute("COMMENT ON COLUMN public.t_file.uploaded_at IS '파일 업로드 일시'")
    op.execute("COMMENT ON COLUMN public.t_file.uploader_id IS '파일을 업로드한 사용자 ID (선택 사항)'")
    op.execute("COMMENT ON COLUMN public.t_file.options IS '파일 관련 추가 메타데이터 (JSONB 형식)'")
    op.execute("COMMENT ON COLUMN public.t_file.width IS '이미지 가로 해상도 (px)'")
    op.execute("COMMENT ON COLUMN public.t_file.height IS '이미지 세로 해상도 (px)'")

    # -- t_image_process --
    op.execute("COMMENT ON COLUMN public.t_image_process.id IS '세션 고유 식별자 (UUID)'")
    op.execute("COMMENT ON COLUMN public.t_image_process.nm IS '사용자 지정 프로세스 명칭 (검색 및 식별용 별칭)'")
    op.execute("COMMENT ON COLUMN public.t_image_process.file_id IS '원본 파일 ID (t_file 참조)'")
    op.execute("COMMENT ON COLUMN public.t_image_process.final_file_id IS '최종 연산 결과 파일 ID (t_file 참조)'")
    op.execute("COMMENT ON COLUMN public.t_image_process.is_latest IS '해당 원본에 대한 최신 편집본 여부'")
    op.execute("COMMENT ON COLUMN public.t_image_process.created_at IS '세션 생성 일시'")
    op.execute("COMMENT ON COLUMN public.t_image_process.updated_at IS '최종 수정 일시'")
    op.execute("COMMENT ON COLUMN public.t_image_process.total_execution_ms IS '전체 연산에 소요된 총 시간 (밀리초, ms)'")

    # -- t_preset --
    op.execute("COMMENT ON COLUMN public.t_preset.id IS '프리셋 고유 식별자 (UUID)'")
    op.execute("COMMENT ON COLUMN public.t_preset.nm IS '프리셋 명칭 (예: 고대비 흑백, 인물 보정 등 사용자 식별용)'")
    op.execute("COMMENT ON COLUMN public.t_preset.description IS '프리셋에 대한 상세 설명 및 용도'")
    op.execute("COMMENT ON COLUMN public.t_preset.is_system IS '시스템 기본 제공 여부 (TRUE일 경우 일반 사용자 삭제 제한 권장)'")
    op.execute("COMMENT ON COLUMN public.t_preset.created_at IS '프리셋 생성 일시'")
    op.execute("COMMENT ON COLUMN public.t_preset.updated_at IS '프리셋 최종 수정 일시'")

    # -- t_preset_step --
    op.execute("COMMENT ON COLUMN public.t_preset_step.id IS '프리셋 단계 고유 식별자 (UUID)'")
    op.execute("COMMENT ON COLUMN public.t_preset_step.preset_id IS '소속된 프리셋 마스터 ID (t_preset 참조)'")
    op.execute("COMMENT ON COLUMN public.t_preset_step.parent_id IS '부모 노드 ID (NULL이면 루트/시작점, 값이 있으면 해당 노드의 결과를 입력으로 받음)'")
    op.execute("COMMENT ON COLUMN public.t_preset_step.step_order IS '동일 부모 내에서 노드 간의 정렬 순서 (0부터 시작)'")
    op.execute("COMMENT ON COLUMN public.t_preset_step.algorithm_nm IS '적용할 알고리즘 식별 명칭 (예: gaussian_blur, canny_edge 등)'")
    op.execute("COMMENT ON COLUMN public.t_preset_step.parameters IS '해당 알고리즘 노드의 기본 설정값 (JSONB 형태)'")
    op.execute("COMMENT ON COLUMN public.t_preset_step.created_at IS '생성일자'")

    # -- t_process_step --
    op.execute("COMMENT ON COLUMN public.t_process_step.id IS '단계 고유 식별자 (UUID)'")
    op.execute("COMMENT ON COLUMN public.t_process_step.process_id IS '소속된 편집 세션 ID (t_image_process 참조)'")
    op.execute("COMMENT ON COLUMN public.t_process_step.parent_id IS '부모 노드 ID (NULL이면 시작점, 값이 있으면 이전 노드의 출력값을 입력으로 받는 트리 구조)'")
    op.execute("COMMENT ON COLUMN public.t_process_step.preset_id IS '이 단계를 생성할 때 참조한 프리셋 ID (선택 사항)'")
    op.execute("COMMENT ON COLUMN public.t_process_step.step_order IS '동일 부모 내에서의 노드 정렬 순서 (0부터 시작)'")
    op.execute("COMMENT ON COLUMN public.t_process_step.algorithm_nm IS '적용된 알고리즘 식별 명칭 (예: gaussian_blur, sharpen 등)'")
    op.execute("COMMENT ON COLUMN public.t_process_step.parameters IS '실제 연산에 사용된 파라미터 값 (Pydantic 모델 스냅샷)'")
    op.execute("COMMENT ON COLUMN public.t_process_step.execution_ms IS '해당 노드의 알고리즘 연산 소요 시간 (밀리초 단위)'")
    op.execute("COMMENT ON COLUMN public.t_process_step.is_enabled IS '해당 노드의 활성화 여부 (비활성화 시 하위 트리 연산에 영향)'")
    op.execute("COMMENT ON COLUMN public.t_process_step.created_at IS '노드 생성 일시'")


def downgrade() -> None:
    # COMMENT 제거 (NULL로 설정)
    for table in ['t_custom_filter', 't_file', 't_image_process', 't_preset', 't_preset_step', 't_process_step']:
        op.execute(f"""
            DO $$
            DECLARE col record;
            BEGIN
                FOR col IN SELECT column_name FROM information_schema.columns WHERE table_name = '{table}' AND table_schema = 'public'
                LOOP
                    EXECUTE format('COMMENT ON COLUMN public.{table}.%I IS NULL', col.column_name);
                END LOOP;
            END $$
        """)
