from datetime import datetime
from typing import Any

from pydantic import Field

from app.schemas.file import CamelModel


class ProcessStepBase(CamelModel):
    algorithm_nm: str = Field(..., description="알고리즘 식별 명칭")
    step_order: int = Field(..., ge=0, description="적용 순서 (0부터)")
    parameters: dict[str, Any] = Field(default_factory=dict, description="알고리즘 파라미터")
    is_enabled: bool = Field(True, description="활성화 여부")
    preset_id: str | None = Field(None, description="참조 프리셋 ID")
    parent_id: str | None = Field(None, description="부모 노드 ID (NULL이면 루트)")


class ProcessStepCreate(ProcessStepBase):
    client_id: str | None = Field(None, description="클라이언트 측 임시 노드 ID (부모 참조용)")
    parent_client_id: str | None = Field(None, description="부모 노드의 client_id (NULL이면 루트)")


class ProcessStepResponse(ProcessStepBase):
    id: str = Field(..., description="단계 ID")
    process_id: str = Field(..., description="소속 프로세스 ID")
    created_at: datetime = Field(..., description="생성 일시")
    execution_ms: int | None = Field(None, description="연산 소요 시간 (ms)")


class ProcessCreate(CamelModel):
    nm: str = Field(..., description="프로세스 명칭")
    file_id: str = Field(..., description="원본 파일 ID")
    steps: list[ProcessStepCreate] = Field(default_factory=list, description="처리 단계 목록")


class ProcessUpdate(CamelModel):
    nm: str | None = Field(None, description="프로세스 명칭")
    final_file_id: str | None = Field(None, description="최종 결과 파일 ID")
    is_latest: bool | None = Field(None, description="최신 편집본 여부")
    total_execution_ms: int | None = Field(None, description="전체 연산 소요 시간 (ms)")
    steps: list[ProcessStepCreate] | None = Field(None, description="처리 단계 목록 (전체 교체)")


class ProcessResponse(CamelModel):
    id: str = Field(..., description="프로세스 ID")
    nm: str = Field(..., description="프로세스 명칭")
    file_id: str = Field(..., description="원본 파일 ID")
    file_path: str | None = Field(None, description="원본 파일 경로 (t_file.path)")
    final_file_id: str | None = Field(None, description="최종 결과 파일 ID")
    is_latest: bool = Field(..., description="최신 편집본 여부")
    total_execution_ms: int | None = Field(None, description="전체 연산 소요 시간 (ms)")
    created_at: datetime = Field(..., description="생성 일시")
    updated_at: datetime = Field(..., description="수정 일시")
    steps: list[ProcessStepResponse] = Field(default_factory=list, description="처리 단계 목록")


class ProcessListResponse(CamelModel):
    items: list[ProcessResponse] = Field(..., description="프로세스 목록")
