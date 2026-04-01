"""uuid to sequence pk

Revision ID: a1b2c3d4e5f6
Revises: f00573979019
Create Date: 2026-04-01 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'f00573979019'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 기존 테이블 DROP (FK 의존성 순서)
    op.execute("DROP TABLE IF EXISTS public.t_process_step CASCADE")
    op.execute("DROP TABLE IF EXISTS public.t_preset_step CASCADE")
    op.execute("DROP TABLE IF EXISTS public.t_image_process CASCADE")
    op.execute("DROP TABLE IF EXISTS public.t_preset CASCADE")
    op.execute("DROP TABLE IF EXISTS public.t_file CASCADE")
    op.execute("DROP TABLE IF EXISTS public.t_custom_filter CASCADE")

    # pgcrypto 더 이상 불필요
    op.execute("DROP EXTENSION IF EXISTS pgcrypto")

    # -- tables (BIGSERIAL PK) --

    op.execute("""
        CREATE TABLE public.t_custom_filter (
            id bigserial NOT NULL,
            nm character varying(100) NOT NULL,
            description text DEFAULT ''::text,
            code text NOT NULL,
            params jsonb DEFAULT '{}'::jsonb,
            version integer DEFAULT 1,
            created_at timestamp with time zone DEFAULT now(),
            updated_at timestamp with time zone DEFAULT now()
        )
    """)

    op.execute("""
        CREATE TABLE public.t_file (
            id bigserial NOT NULL,
            origin_nm text NOT NULL,
            nm text NOT NULL,
            path text NOT NULL,
            mime_type text NOT NULL,
            size_bytes bigint NOT NULL,
            uploaded_at timestamp with time zone DEFAULT now() NOT NULL,
            uploader_id bigint,
            options jsonb DEFAULT '{}'::jsonb NOT NULL,
            content_hash text,
            width integer,
            height integer,
            CONSTRAINT t_file_mime_type_check CHECK ((mime_type = ANY (ARRAY['image/png'::text, 'image/jpeg'::text, 'image/webp'::text, 'image/bmp'::text, 'image/tiff'::text]))),
            CONSTRAINT t_file_size_bytes_check CHECK ((size_bytes > 0))
        )
    """)

    op.execute("""
        CREATE TABLE public.t_image_process (
            id bigserial NOT NULL,
            nm text NOT NULL,
            file_id bigint NOT NULL,
            final_file_id bigint,
            is_latest boolean DEFAULT true,
            created_at timestamp with time zone DEFAULT now() NOT NULL,
            updated_at timestamp with time zone DEFAULT now() NOT NULL,
            total_execution_ms bigint
        )
    """)

    op.execute("""
        CREATE TABLE public.t_preset (
            id bigserial NOT NULL,
            nm text NOT NULL,
            description text,
            is_system boolean DEFAULT false NOT NULL,
            created_at timestamp with time zone DEFAULT now() NOT NULL,
            updated_at timestamp with time zone DEFAULT now() NOT NULL
        )
    """)

    op.execute("""
        CREATE TABLE public.t_preset_step (
            id bigserial NOT NULL,
            preset_id bigint NOT NULL,
            parent_id bigint,
            step_order integer DEFAULT 0 NOT NULL,
            algorithm_nm text NOT NULL,
            parameters jsonb DEFAULT '{}'::jsonb NOT NULL,
            created_at timestamp with time zone DEFAULT now() NOT NULL,
            CONSTRAINT t_preset_step_order_check CHECK ((step_order >= 0))
        )
    """)

    op.execute("""
        CREATE TABLE public.t_process_step (
            id bigserial NOT NULL,
            process_id bigint NOT NULL,
            parent_id bigint,
            preset_id bigint,
            step_order integer NOT NULL,
            algorithm_nm text NOT NULL,
            parameters jsonb DEFAULT '{}'::jsonb NOT NULL,
            execution_ms bigint,
            is_enabled boolean DEFAULT true NOT NULL,
            created_at timestamp with time zone DEFAULT now() NOT NULL,
            CONSTRAINT t_process_step_order_check CHECK ((step_order >= 0))
        )
    """)

    # -- PK --

    op.execute("ALTER TABLE ONLY public.t_custom_filter ADD CONSTRAINT t_custom_filter_pkey PRIMARY KEY (id)")
    op.execute("ALTER TABLE ONLY public.t_file ADD CONSTRAINT t_file_pkey PRIMARY KEY (id)")
    op.execute("ALTER TABLE ONLY public.t_image_process ADD CONSTRAINT t_image_process_pkey PRIMARY KEY (id)")
    op.execute("ALTER TABLE ONLY public.t_preset ADD CONSTRAINT t_preset_pkey PRIMARY KEY (id)")
    op.execute("ALTER TABLE ONLY public.t_preset_step ADD CONSTRAINT t_preset_step_pkey PRIMARY KEY (id)")
    op.execute("ALTER TABLE ONLY public.t_process_step ADD CONSTRAINT t_process_step_pkey PRIMARY KEY (id)")

    # -- indexes --

    op.execute("CREATE INDEX ix_t_file_uploaded_at ON public.t_file USING btree (uploaded_at DESC)")
    op.execute("CREATE INDEX ix_t_image_process_file_id ON public.t_image_process USING btree (file_id)")
    op.execute("CREATE INDEX ix_t_process_step_parent_id ON public.t_process_step USING btree (parent_id)")
    op.execute("CREATE INDEX ix_t_process_step_process_id ON public.t_process_step USING btree (process_id)")
    op.execute("CREATE UNIQUE INDEX uq_t_file_content_hash ON public.t_file USING btree (content_hash) WHERE (content_hash IS NOT NULL)")

    # -- FK --

    op.execute("ALTER TABLE ONLY public.t_preset_step ADD CONSTRAINT fk_preset_master FOREIGN KEY (preset_id) REFERENCES public.t_preset(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE ONLY public.t_preset_step ADD CONSTRAINT fk_preset_parent FOREIGN KEY (parent_id) REFERENCES public.t_preset_step(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE ONLY public.t_image_process ADD CONSTRAINT fk_process_file FOREIGN KEY (file_id) REFERENCES public.t_file(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE ONLY public.t_image_process ADD CONSTRAINT fk_process_final_file FOREIGN KEY (final_file_id) REFERENCES public.t_file(id)")
    op.execute("ALTER TABLE ONLY public.t_process_step ADD CONSTRAINT fk_step_parent FOREIGN KEY (parent_id) REFERENCES public.t_process_step(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE ONLY public.t_process_step ADD CONSTRAINT fk_step_preset FOREIGN KEY (preset_id) REFERENCES public.t_preset(id) ON DELETE SET NULL")
    op.execute("ALTER TABLE ONLY public.t_process_step ADD CONSTRAINT fk_step_process FOREIGN KEY (process_id) REFERENCES public.t_image_process(id) ON DELETE CASCADE")

    # -- column comments --

    op.execute("COMMENT ON COLUMN public.t_custom_filter.id IS '필터 고유 식별자'")
    op.execute("COMMENT ON COLUMN public.t_custom_filter.nm IS '필터 이름 (사용자 노출용)'")
    op.execute("COMMENT ON COLUMN public.t_custom_filter.description IS '필터 상세 설명'")
    op.execute("COMMENT ON COLUMN public.t_custom_filter.code IS '필터 파이썬 코드'")
    op.execute("COMMENT ON COLUMN public.t_custom_filter.params IS '필터 실행에 필요한 파라미터 정의 (JSON 형식)'")
    op.execute("COMMENT ON COLUMN public.t_custom_filter.version IS '필터 버전 관리 번호'")
    op.execute("COMMENT ON COLUMN public.t_custom_filter.created_at IS '데이터 생성 일시'")
    op.execute("COMMENT ON COLUMN public.t_custom_filter.updated_at IS '데이터 최종 수정 일시'")

    op.execute("COMMENT ON COLUMN public.t_file.id IS '파일 고유 식별자'")
    op.execute("COMMENT ON COLUMN public.t_file.origin_nm IS '사용자가 업로드할 당시의 실제 파일명 (예: photo.jpg)'")
    op.execute("COMMENT ON COLUMN public.t_file.nm IS '서버 스토리지에 저장된 고유 파일명'")
    op.execute("COMMENT ON COLUMN public.t_file.path IS '파일이 저장된 물리적 경로'")
    op.execute("COMMENT ON COLUMN public.t_file.mime_type IS '파일의 MIME 타입 (image/png, image/jpeg만 허용)'")
    op.execute("COMMENT ON COLUMN public.t_file.size_bytes IS '파일 크기 (바이트 단위)'")
    op.execute("COMMENT ON COLUMN public.t_file.uploaded_at IS '파일 업로드 일시'")
    op.execute("COMMENT ON COLUMN public.t_file.uploader_id IS '파일을 업로드한 사용자 ID (선택 사항)'")
    op.execute("COMMENT ON COLUMN public.t_file.options IS '파일 관련 추가 메타데이터 (JSONB 형식)'")
    op.execute("COMMENT ON COLUMN public.t_file.width IS '이미지 가로 해상도 (px)'")
    op.execute("COMMENT ON COLUMN public.t_file.height IS '이미지 세로 해상도 (px)'")

    op.execute("COMMENT ON COLUMN public.t_image_process.id IS '세션 고유 식별자'")
    op.execute("COMMENT ON COLUMN public.t_image_process.nm IS '사용자 지정 프로세스 명칭'")
    op.execute("COMMENT ON COLUMN public.t_image_process.file_id IS '원본 파일 ID (t_file 참조)'")
    op.execute("COMMENT ON COLUMN public.t_image_process.final_file_id IS '최종 연산 결과 파일 ID (t_file 참조)'")
    op.execute("COMMENT ON COLUMN public.t_image_process.is_latest IS '해당 원본에 대한 최신 편집본 여부'")
    op.execute("COMMENT ON COLUMN public.t_image_process.created_at IS '세션 생성 일시'")
    op.execute("COMMENT ON COLUMN public.t_image_process.updated_at IS '최종 수정 일시'")
    op.execute("COMMENT ON COLUMN public.t_image_process.total_execution_ms IS '전체 연산에 소요된 총 시간 (밀리초, ms)'")

    op.execute("COMMENT ON COLUMN public.t_preset.id IS '프리셋 고유 식별자'")
    op.execute("COMMENT ON COLUMN public.t_preset.nm IS '프리셋 명칭'")
    op.execute("COMMENT ON COLUMN public.t_preset.description IS '프리셋에 대한 상세 설명 및 용도'")
    op.execute("COMMENT ON COLUMN public.t_preset.is_system IS '시스템 기본 제공 여부'")
    op.execute("COMMENT ON COLUMN public.t_preset.created_at IS '프리셋 생성 일시'")
    op.execute("COMMENT ON COLUMN public.t_preset.updated_at IS '프리셋 최종 수정 일시'")

    op.execute("COMMENT ON COLUMN public.t_preset_step.id IS '프리셋 단계 고유 식별자'")
    op.execute("COMMENT ON COLUMN public.t_preset_step.preset_id IS '소속된 프리셋 마스터 ID (t_preset 참조)'")
    op.execute("COMMENT ON COLUMN public.t_preset_step.parent_id IS '부모 노드 ID (NULL이면 루트)'")
    op.execute("COMMENT ON COLUMN public.t_preset_step.step_order IS '동일 부모 내에서 노드 간의 정렬 순서 (0부터 시작)'")
    op.execute("COMMENT ON COLUMN public.t_preset_step.algorithm_nm IS '적용할 알고리즘 식별 명칭'")
    op.execute("COMMENT ON COLUMN public.t_preset_step.parameters IS '해당 알고리즘 노드의 기본 설정값 (JSONB 형태)'")
    op.execute("COMMENT ON COLUMN public.t_preset_step.created_at IS '생성일자'")

    op.execute("COMMENT ON COLUMN public.t_process_step.id IS '단계 고유 식별자'")
    op.execute("COMMENT ON COLUMN public.t_process_step.process_id IS '소속된 편집 세션 ID (t_image_process 참조)'")
    op.execute("COMMENT ON COLUMN public.t_process_step.parent_id IS '부모 노드 ID (NULL이면 시작점)'")
    op.execute("COMMENT ON COLUMN public.t_process_step.preset_id IS '이 단계를 생성할 때 참조한 프리셋 ID (선택 사항)'")
    op.execute("COMMENT ON COLUMN public.t_process_step.step_order IS '동일 부모 내에서의 노드 정렬 순서 (0부터 시작)'")
    op.execute("COMMENT ON COLUMN public.t_process_step.algorithm_nm IS '적용된 알고리즘 식별 명칭'")
    op.execute("COMMENT ON COLUMN public.t_process_step.parameters IS '실제 연산에 사용된 파라미터 값'")
    op.execute("COMMENT ON COLUMN public.t_process_step.execution_ms IS '해당 노드의 알고리즘 연산 소요 시간 (밀리초 단위)'")
    op.execute("COMMENT ON COLUMN public.t_process_step.is_enabled IS '해당 노드의 활성화 여부'")
    op.execute("COMMENT ON COLUMN public.t_process_step.created_at IS '노드 생성 일시'")


def downgrade() -> None:
    # downgrade는 지원하지 않음 (데이터 손실 발생)
    raise NotImplementedError("Downgrade not supported: UUID to Sequence migration is destructive")
