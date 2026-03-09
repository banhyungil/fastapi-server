-- public.t_file definition

-- Drop table

-- DROP TABLE public.t_file;

CREATE TABLE public.t_file ( id uuid DEFAULT gen_random_uuid() NOT NULL , origin_nm text NOT NULL , nm text NOT NULL , "path" text NOT NULL , mime_type text NOT NULL , size_bytes int8 NOT NULL , uploaded_at timestamptz DEFAULT now() NOT NULL , uploader_id uuid NULL , "options" jsonb DEFAULT '{}'::jsonb NOT NULL , content_hash text NULL , CONSTRAINT t_file_mime_type_check CHECK ((mime_type = ANY (ARRAY['image/png'::text, 'image/jpeg'::text, 'image/webp'::text]))), CONSTRAINT t_file_pkey PRIMARY KEY (id), CONSTRAINT t_file_size_bytes_check CHECK ((size_bytes > 0)));
CREATE INDEX ix_t_file_uploaded_at ON public.t_file USING btree (uploaded_at DESC);
CREATE UNIQUE INDEX uq_t_file_content_hash ON public.t_file USING btree (content_hash) WHERE content_hash IS NOT NULL;
COMMENT ON TABLE public.t_file IS '물리 파일 정보: 시스템에 업로드된 원본 및 결과물 파일의 메타데이터를 저장함';

-- Column comments

COMMENT ON COLUMN public.t_file.id IS '파일 고유 식별자 (UUID)';
COMMENT ON COLUMN public.t_file.origin_nm IS '사용자가 업로드할 당시의 실제 파일명 (예: photo.jpg)';
COMMENT ON COLUMN public.t_file.nm IS '서버 스토리지에 저장된 고유 파일명 (중복 방지용 UUID/타임스탬프 조합)';
COMMENT ON COLUMN public.t_file."path" IS '파일이 저장된 물리적 또는 클라우드 경로';
COMMENT ON COLUMN public.t_file.mime_type IS '파일의 MIME 타입 (image/png, image/jpeg만 허용)';
COMMENT ON COLUMN public.t_file.size_bytes IS '파일 크기 (바이트 단위)';
COMMENT ON COLUMN public.t_file.uploaded_at IS '파일 업로드 일시';
COMMENT ON COLUMN public.t_file.uploader_id IS '파일을 업로드한 사용자 ID (선택 사항)';
COMMENT ON COLUMN public.t_file."options" IS '파일 관련 추가 메타데이터 (JSONB 형식)';
COMMENT ON COLUMN public.t_file.content_hash IS '파일 콘텐츠 SHA-256 해시 (중복 업로드 방지용)';


-- public.t_preset definition

-- Drop table

-- DROP TABLE public.t_preset;

CREATE TABLE public.t_preset ( id uuid DEFAULT gen_random_uuid() NOT NULL , nm text NOT NULL , description text NULL , is_system bool DEFAULT false NOT NULL , created_at timestamptz DEFAULT now() NOT NULL , updated_at timestamptz DEFAULT now() NOT NULL , CONSTRAINT t_preset_pkey PRIMARY KEY (id));
COMMENT ON TABLE public.t_preset IS '이미지 처리 프리셋 마스터: 재사용 가능한 알고리즘 조합의 메타데이터를 관리함';

-- Column comments

COMMENT ON COLUMN public.t_preset.id IS '프리셋 고유 식별자 (UUID)';
COMMENT ON COLUMN public.t_preset.nm IS '프리셋 명칭 (예: 고대비 흑백, 인물 보정 등 사용자 식별용)';
COMMENT ON COLUMN public.t_preset.description IS '프리셋에 대한 상세 설명 및 용도';
COMMENT ON COLUMN public.t_preset.is_system IS '시스템 기본 제공 여부 (TRUE일 경우 일반 사용자 삭제 제한 권장)';
COMMENT ON COLUMN public.t_preset.created_at IS '프리셋 생성 일시';
COMMENT ON COLUMN public.t_preset.updated_at IS '프리셋 최종 수정 일시';


-- public.t_image_process definition

-- Drop table

-- DROP TABLE public.t_image_process;

CREATE TABLE public.t_image_process ( id uuid DEFAULT gen_random_uuid() NOT NULL , nm text NOT NULL , file_id uuid NOT NULL , final_file_id uuid NULL , is_latest bool DEFAULT true NULL , created_at timestamptz DEFAULT now() NOT NULL , updated_at timestamptz DEFAULT now() NOT NULL , total_execution_ms int8 NULL , CONSTRAINT t_image_process_pkey PRIMARY KEY (id), CONSTRAINT fk_process_file FOREIGN KEY (file_id) REFERENCES public.t_file(id) ON DELETE CASCADE, CONSTRAINT fk_process_final_file FOREIGN KEY (final_file_id) REFERENCES public.t_file(id));
CREATE INDEX ix_t_image_process_file_id ON public.t_image_process USING btree (file_id);
COMMENT ON TABLE public.t_image_process IS '이미지 편집 세션 정보: 원본 파일과 최종 결과물을 연결하고 편집 이력을 관리함';

-- Column comments

COMMENT ON COLUMN public.t_image_process.id IS '세션 고유 식별자 (UUID)';
COMMENT ON COLUMN public.t_image_process.nm IS '사용자 지정 프로세스 명칭 (검색 및 식별용 별칭)';
COMMENT ON COLUMN public.t_image_process.file_id IS '원본 파일 ID (t_file 참조)';
COMMENT ON COLUMN public.t_image_process.final_file_id IS '최종 연산 결과 파일 ID (t_file 참조)';
COMMENT ON COLUMN public.t_image_process.is_latest IS '해당 원본에 대한 최신 편집본 여부';
COMMENT ON COLUMN public.t_image_process.created_at IS '세션 생성 일시';
COMMENT ON COLUMN public.t_image_process.updated_at IS '최종 수정 일시';
COMMENT ON COLUMN public.t_image_process.total_execution_ms IS '전체 연산에 소요된 총 시간 (밀리초, ms)';

-- public.t_preset_step definition

-- Drop table

-- DROP TABLE public.t_preset_step;

CREATE TABLE public.t_preset_step ( id uuid DEFAULT gen_random_uuid() NOT NULL , preset_id uuid NOT NULL , parent_id uuid NULL , step_order int4 DEFAULT 0 NOT NULL , algorithm_nm text NOT NULL , parameters jsonb DEFAULT '{}'::jsonb NOT NULL , created_at timestamptz DEFAULT now() NOT NULL , CONSTRAINT t_preset_step_order_check CHECK ((step_order >= 0)), CONSTRAINT t_preset_step_pkey PRIMARY KEY (id));
COMMENT ON TABLE public.t_preset_step IS '프리셋 상세 단계: 트리 구조의 알고리즘 설계도를 저장하여 복합 연산 흐름을 정의함';

-- Column comments

COMMENT ON COLUMN public.t_preset_step.id IS '프리셋 단계 고유 식별자 (UUID)';
COMMENT ON COLUMN public.t_preset_step.preset_id IS '소속된 프리셋 마스터 ID (t_preset 참조)';
COMMENT ON COLUMN public.t_preset_step.parent_id IS '부모 노드 ID (NULL이면 루트/시작점, 값이 있으면 해당 노드의 결과를 입력으로 받음)';
COMMENT ON COLUMN public.t_preset_step.step_order IS '동일 부모 내에서 노드 간의 정렬 순서 (0부터 시작)';
COMMENT ON COLUMN public.t_preset_step.algorithm_nm IS '적용할 알고리즘 식별 명칭 (예: gaussian_blur, canny_edge 등)';
COMMENT ON COLUMN public.t_preset_step.parameters IS '해당 알고리즘 노드의 기본 설정값 (JSONB 형태)';
COMMENT ON COLUMN public.t_preset_step.created_at IS '생성일자';


-- public.t_process_step definition

-- Drop table

-- DROP TABLE public.t_process_step;

CREATE TABLE public.t_process_step ( id uuid DEFAULT gen_random_uuid() NOT NULL , process_id uuid NOT NULL , parent_id uuid NULL , preset_id uuid NULL , step_order int4 NOT NULL , algorithm_nm text NOT NULL , parameters jsonb DEFAULT '{}'::jsonb NOT NULL , execution_ms int8 NULL , is_enabled bool DEFAULT true NOT NULL , created_at timestamptz DEFAULT now() NOT NULL , CONSTRAINT t_process_step_order_check CHECK ((step_order >= 0)), CONSTRAINT t_process_step_pkey PRIMARY KEY (id));
CREATE INDEX ix_t_process_step_parent_id ON public.t_process_step USING btree (parent_id);
CREATE INDEX ix_t_process_step_process_id ON public.t_process_step USING btree (process_id);
COMMENT ON TABLE public.t_process_step IS '이미지 처리 상세 단계: 실제 작업 세션에 적용된 알고리즘 노드들의 트리 구조와 실행 이력을 저장함';

-- Column comments

COMMENT ON COLUMN public.t_process_step.id IS '단계 고유 식별자 (UUID)';
COMMENT ON COLUMN public.t_process_step.process_id IS '소속된 편집 세션 ID (t_image_process 참조)';
COMMENT ON COLUMN public.t_process_step.parent_id IS '부모 노드 ID (NULL이면 시작점, 값이 있으면 이전 노드의 출력값을 입력으로 받는 트리 구조)';
COMMENT ON COLUMN public.t_process_step.preset_id IS '이 단계를 생성할 때 참조한 프리셋 ID (선택 사항)';
COMMENT ON COLUMN public.t_process_step.step_order IS '동일 부모 내에서의 노드 정렬 순서 (0부터 시작)';
COMMENT ON COLUMN public.t_process_step.algorithm_nm IS '적용된 알고리즘 식별 명칭 (예: gaussian_blur, sharpen 등)';
COMMENT ON COLUMN public.t_process_step.parameters IS '실제 연산에 사용된 파라미터 값 (Pydantic 모델 스냅샷)';
COMMENT ON COLUMN public.t_process_step.execution_ms IS '해당 노드의 알고리즘 연산 소요 시간 (밀리초 단위)';
COMMENT ON COLUMN public.t_process_step.is_enabled IS '해당 노드의 활성화 여부 (비활성화 시 하위 트리 연산에 영향)';
COMMENT ON COLUMN public.t_process_step.created_at IS '노드 생성 일시';


-- public.t_preset_step foreign keys

ALTER TABLE public.t_preset_step ADD CONSTRAINT fk_preset_master FOREIGN KEY (preset_id) REFERENCES public.t_preset(id) ON DELETE CASCADE;
ALTER TABLE public.t_preset_step ADD CONSTRAINT fk_preset_parent FOREIGN KEY (parent_id) REFERENCES public.t_preset_step(id) ON DELETE CASCADE;


-- public.t_process_step foreign keys

ALTER TABLE public.t_process_step ADD CONSTRAINT fk_step_parent FOREIGN KEY (parent_id) REFERENCES public.t_process_step(id) ON DELETE CASCADE;
ALTER TABLE public.t_process_step ADD CONSTRAINT fk_step_preset FOREIGN KEY (preset_id) REFERENCES public.t_preset(id) ON DELETE SET NULL;
ALTER TABLE public.t_process_step ADD CONSTRAINT fk_step_process FOREIGN KEY (process_id) REFERENCES public.t_image_process(id) ON DELETE CASCADE;