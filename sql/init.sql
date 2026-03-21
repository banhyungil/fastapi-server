-- 확장 모듈
CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;

-- ENUM 타입
CREATE TYPE public.image_job_status AS ENUM (
    'pending',
    'done',
    'failed'
);

-- ── 테이블 ───────────────────────────────────────────────────────────────────

CREATE TABLE public.t_custom_filter (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    nm character varying(100) NOT NULL,
    description text DEFAULT ''::text,
    code text NOT NULL,
    params jsonb DEFAULT '{}'::jsonb,
    version integer DEFAULT 1,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);

COMMENT ON TABLE public.t_custom_filter IS '사용자 정의 이미지 프로세싱 필터/알고리즘 관리 테이블';

CREATE TABLE public.t_file (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    origin_nm text NOT NULL,
    nm text NOT NULL,
    path text NOT NULL,
    mime_type text NOT NULL,
    size_bytes bigint NOT NULL,
    uploaded_at timestamp with time zone DEFAULT now() NOT NULL,
    uploader_id uuid,
    options jsonb DEFAULT '{}'::jsonb NOT NULL,
    content_hash text,
    width integer,
    height integer,
    CONSTRAINT t_file_mime_type_check CHECK ((mime_type = ANY (ARRAY['image/png'::text, 'image/jpeg'::text, 'image/webp'::text, 'image/bmp'::text, 'image/tiff'::text]))),
    CONSTRAINT t_file_size_bytes_check CHECK ((size_bytes > 0))
);

COMMENT ON TABLE public.t_file IS '물리 파일 정보: 시스템에 업로드된 원본 및 결과물 파일의 메타데이터를 저장함';

CREATE TABLE public.t_image_process (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    nm text NOT NULL,
    file_id uuid NOT NULL,
    final_file_id uuid,
    is_latest boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    total_execution_ms bigint
);

COMMENT ON TABLE public.t_image_process IS '이미지 편집 세션 정보: 원본 파일과 최종 결과물을 연결하고 편집 이력을 관리함';

CREATE TABLE public.t_preset (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    nm text NOT NULL,
    description text,
    is_system boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);

COMMENT ON TABLE public.t_preset IS '이미지 처리 프리셋 마스터: 재사용 가능한 알고리즘 조합의 메타데이터를 관리함';

CREATE TABLE public.t_preset_step (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    preset_id uuid NOT NULL,
    parent_id uuid,
    step_order integer DEFAULT 0 NOT NULL,
    algorithm_nm text NOT NULL,
    parameters jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT t_preset_step_order_check CHECK ((step_order >= 0))
);

COMMENT ON TABLE public.t_preset_step IS '프리셋 상세 단계: 트리 구조의 알고리즘 설계도를 저장하여 복합 연산 흐름을 정의함';

CREATE TABLE public.t_process_step (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    process_id uuid NOT NULL,
    parent_id uuid,
    preset_id uuid,
    step_order integer NOT NULL,
    algorithm_nm text NOT NULL,
    parameters jsonb DEFAULT '{}'::jsonb NOT NULL,
    execution_ms bigint,
    is_enabled boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT t_process_step_order_check CHECK ((step_order >= 0))
);

COMMENT ON TABLE public.t_process_step IS '이미지 처리 상세 단계: 실제 작업 세션에 적용된 알고리즘 노드들의 트리 구조와 실행 이력을 저장함';

-- ── PK ───────────────────────────────────────────────────────────────────────

ALTER TABLE ONLY public.t_custom_filter ADD CONSTRAINT t_custom_filter_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.t_file ADD CONSTRAINT t_file_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.t_image_process ADD CONSTRAINT t_image_process_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.t_preset ADD CONSTRAINT t_preset_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.t_preset_step ADD CONSTRAINT t_preset_step_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.t_process_step ADD CONSTRAINT t_process_step_pkey PRIMARY KEY (id);

-- ── 인덱스 ───────────────────────────────────────────────────────────────────

CREATE INDEX ix_t_file_uploaded_at ON public.t_file USING btree (uploaded_at DESC);
CREATE INDEX ix_t_image_process_file_id ON public.t_image_process USING btree (file_id);
CREATE INDEX ix_t_process_step_parent_id ON public.t_process_step USING btree (parent_id);
CREATE INDEX ix_t_process_step_process_id ON public.t_process_step USING btree (process_id);
CREATE UNIQUE INDEX uq_t_file_content_hash ON public.t_file USING btree (content_hash) WHERE (content_hash IS NOT NULL);

-- ── FK ───────────────────────────────────────────────────────────────────────

ALTER TABLE ONLY public.t_preset_step ADD CONSTRAINT fk_preset_master FOREIGN KEY (preset_id) REFERENCES public.t_preset(id) ON DELETE CASCADE;
ALTER TABLE ONLY public.t_preset_step ADD CONSTRAINT fk_preset_parent FOREIGN KEY (parent_id) REFERENCES public.t_preset_step(id) ON DELETE CASCADE;
ALTER TABLE ONLY public.t_image_process ADD CONSTRAINT fk_process_file FOREIGN KEY (file_id) REFERENCES public.t_file(id) ON DELETE CASCADE;
ALTER TABLE ONLY public.t_image_process ADD CONSTRAINT fk_process_final_file FOREIGN KEY (final_file_id) REFERENCES public.t_file(id);
ALTER TABLE ONLY public.t_process_step ADD CONSTRAINT fk_step_parent FOREIGN KEY (parent_id) REFERENCES public.t_process_step(id) ON DELETE CASCADE;
ALTER TABLE ONLY public.t_process_step ADD CONSTRAINT fk_step_preset FOREIGN KEY (preset_id) REFERENCES public.t_preset(id) ON DELETE SET NULL;
ALTER TABLE ONLY public.t_process_step ADD CONSTRAINT fk_step_process FOREIGN KEY (process_id) REFERENCES public.t_image_process(id) ON DELETE CASCADE;
