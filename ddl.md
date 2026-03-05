-- public.t_file definition

-- Drop table

-- DROP TABLE public.t_file;

CREATE TABLE public.t_file ( id uuid DEFAULT gen_random_uuid() NOT NULL , origin_nm text NOT NULL , nm text NOT NULL , "path" text NOT NULL , mime_type text NOT NULL , size_bytes int8 NOT NULL , uploaded_at timestamptz DEFAULT now() NOT NULL , uploader_id uuid NULL , "options" jsonb DEFAULT '{}'::jsonb NOT NULL , CONSTRAINT t_file_mime_type_check CHECK ((mime_type = ANY (ARRAY['image/png'::text, 'image/jpeg'::text]))), CONSTRAINT t_file_pkey PRIMARY KEY (id), CONSTRAINT t_file_size_bytes_check CHECK ((size_bytes > 0)));
CREATE INDEX ix_t_file_uploaded_at ON public.t_file USING btree (uploaded_at DESC);
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


-- public.t_image_process definition

-- Drop table

-- DROP TABLE public.t_image_process;

CREATE TABLE public.t_image_process ( id uuid DEFAULT gen_random_uuid() NOT NULL , nm text NOT NULL , file_id uuid NOT NULL , final_file_id uuid NULL , is_latest bool DEFAULT true NULL , created_at timestamptz DEFAULT now() NOT NULL , updated_at timestamptz DEFAULT now() NOT NULL , CONSTRAINT t_image_process_pkey PRIMARY KEY (id), CONSTRAINT fk_process_file FOREIGN KEY (file_id) REFERENCES public.t_file(id) ON DELETE CASCADE, CONSTRAINT fk_process_final_file FOREIGN KEY (final_file_id) REFERENCES public.t_file(id));
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


-- public.t_process_step definition

-- Drop table

-- DROP TABLE public.t_process_step;

CREATE TABLE public.t_process_step ( id uuid DEFAULT gen_random_uuid() NOT NULL , process_id uuid NOT NULL , step_order int4 NOT NULL , algorithm_nm text NOT NULL , parameters jsonb DEFAULT '{}'::jsonb NOT NULL , is_enabled bool DEFAULT true NOT NULL , CONSTRAINT t_process_step_order_check CHECK ((step_order >= 0)), CONSTRAINT t_process_step_pkey PRIMARY KEY (id), CONSTRAINT fk_step_process FOREIGN KEY (process_id) REFERENCES public.t_image_process(id) ON DELETE CASCADE);
CREATE INDEX ix_t_process_step_process_id ON public.t_process_step USING btree (process_id, step_order);
COMMENT ON TABLE public.t_process_step IS '이미지 처리 상세 단계: 알고리즘 종류와 파라미터 설정을 순서대로 저장함';

-- Column comments

COMMENT ON COLUMN public.t_process_step.id IS '단계 고유 식별자 (UUID)';
COMMENT ON COLUMN public.t_process_step.process_id IS '소속된 편집 세션 ID (t_image_process 참조)';
COMMENT ON COLUMN public.t_process_step.step_order IS '알고리즘 적용 순서 (0부터 시작)';
COMMENT ON COLUMN public.t_process_step.algorithm_nm IS '적용할 알고리즘 식별 명칭 (예: gaussian_blur, canny_edge)';
COMMENT ON COLUMN public.t_process_step.parameters IS '알고리즘별 설정값 (Pydantic 모델 직렬화 JSON)';
COMMENT ON COLUMN public.t_process_step.is_enabled IS '해당 단계의 활성화 여부 (비활성화 시 연산에서 제외)';