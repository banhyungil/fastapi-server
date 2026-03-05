from datetime import datetime
from typing import Any

from pydantic import Field

from app.schemas.file import CamelModel


class PresetStepBase(CamelModel):
    algorithm_nm: str = Field(..., description="알고리즘 식별 명칭")
    step_order: int = Field(0, ge=0, description="동일 부모 내 정렬 순서 (0부터)")
    parameters: dict[str, Any] = Field(default_factory=dict, description="알고리즘 파라미터")


class PresetStepCreate(PresetStepBase):
    parent_id: str | None = Field(None, description="부모 노드 ID (NULL이면 루트)")


class PresetStepResponse(PresetStepBase):
    id: str = Field(..., description="프리셋 단계 ID")
    parent_id: str | None = Field(None, description="부모 노드 ID")


class PresetCreate(CamelModel):
    nm: str = Field(..., description="프리셋 명칭")
    description: str | None = Field(None, description="프리셋 설명")
    is_system: bool = Field(False, description="시스템 기본 제공 여부")
    steps: list[PresetStepCreate] = Field(default_factory=list, description="프리셋 단계 목록")


class PresetUpdate(CamelModel):
    nm: str | None = Field(None, description="프리셋 명칭")
    description: str | None = Field(None, description="프리셋 설명")
    steps: list[PresetStepCreate] | None = Field(None, description="프리셋 단계 목록 (전체 교체)")


class PresetResponse(CamelModel):
    id: str = Field(..., description="프리셋 ID")
    nm: str = Field(..., description="프리셋 명칭")
    description: str | None = Field(None, description="프리셋 설명")
    is_system: bool = Field(..., description="시스템 기본 제공 여부")
    created_at: datetime = Field(..., description="생성 일시")
    updated_at: datetime = Field(..., description="수정 일시")
    steps: list[PresetStepResponse] = Field(default_factory=list, description="프리셋 단계 목록")


class PresetListResponse(CamelModel):
    items: list[PresetResponse] = Field(..., description="프리셋 목록")
