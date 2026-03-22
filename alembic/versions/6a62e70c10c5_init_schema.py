"""init schema

Revision ID: 6a62e70c10c5
Revises:
Create Date: 2026-03-21 23:45:38.146200

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '6a62e70c10c5'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public")

    op.execute("""
        CREATE TYPE public.image_job_status AS ENUM ('pending', 'done', 'failed')
    """)

    # -- tables --

    op.execute("""
        CREATE TABLE public.t_custom_filter (
            id uuid DEFAULT gen_random_uuid() NOT NULL,
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
        )
    """)

    op.execute("""
        CREATE TABLE public.t_image_process (
            id uuid DEFAULT gen_random_uuid() NOT NULL,
            nm text NOT NULL,
            file_id uuid NOT NULL,
            final_file_id uuid,
            is_latest boolean DEFAULT true,
            created_at timestamp with time zone DEFAULT now() NOT NULL,
            updated_at timestamp with time zone DEFAULT now() NOT NULL,
            total_execution_ms bigint
        )
    """)

    op.execute("""
        CREATE TABLE public.t_preset (
            id uuid DEFAULT gen_random_uuid() NOT NULL,
            nm text NOT NULL,
            description text,
            is_system boolean DEFAULT false NOT NULL,
            created_at timestamp with time zone DEFAULT now() NOT NULL,
            updated_at timestamp with time zone DEFAULT now() NOT NULL
        )
    """)

    op.execute("""
        CREATE TABLE public.t_preset_step (
            id uuid DEFAULT gen_random_uuid() NOT NULL,
            preset_id uuid NOT NULL,
            parent_id uuid,
            step_order integer DEFAULT 0 NOT NULL,
            algorithm_nm text NOT NULL,
            parameters jsonb DEFAULT '{}'::jsonb NOT NULL,
            created_at timestamp with time zone DEFAULT now() NOT NULL,
            CONSTRAINT t_preset_step_order_check CHECK ((step_order >= 0))
        )
    """)

    op.execute("""
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


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS public.t_process_step CASCADE")
    op.execute("DROP TABLE IF EXISTS public.t_preset_step CASCADE")
    op.execute("DROP TABLE IF EXISTS public.t_image_process CASCADE")
    op.execute("DROP TABLE IF EXISTS public.t_preset CASCADE")
    op.execute("DROP TABLE IF EXISTS public.t_file CASCADE")
    op.execute("DROP TABLE IF EXISTS public.t_custom_filter CASCADE")
    op.execute("DROP TYPE IF EXISTS public.image_job_status")
