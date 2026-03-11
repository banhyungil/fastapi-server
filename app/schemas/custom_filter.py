from datetime import datetime
from typing import Any

from pydantic import Field

from app.schemas.file import CamelModel


class CustomFilterCreate(CamelModel):
    nm: str = Field(..., description="커스텀 필터 이름")
    description: str = Field("", description="필터 설명")
    code: str = Field(..., description="Python 필터 코드")
    params: dict[str, Any] = Field(
        default_factory=dict,
        description="기본 파라미터 정의 (key, type, default)",
    )


class CustomFilterUpdate(CamelModel):
    nm: str | None = Field(None, description="커스텀 필터 이름")
    description: str | None = Field(None, description="필터 설명")
    code: str | None = Field(None, description="Python 필터 코드")
    params: dict[str, Any] | None = Field(None, description="기본 파라미터 정의")


class CustomFilterResponse(CamelModel):
    id: str = Field(..., description="커스텀 필터 ID (UUID)")
    nm: str = Field(..., description="커스텀 필터 이름")
    description: str = Field("", description="필터 설명")
    code: str = Field(..., description="Python 필터 코드")
    params: dict[str, Any] = Field(default_factory=dict, description="기본 파라미터 정의")
    version: int = Field(..., description="코드 버전")
    created_at: datetime = Field(..., description="생성 일시")
    updated_at: datetime = Field(..., description="수정 일시")


class CustomFilterListResponse(CamelModel):
    items: list[CustomFilterResponse] = Field(..., description="커스텀 필터 목록")
