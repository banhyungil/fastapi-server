from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.files_schema import CamelModel


class SelectOption(BaseModel):
    label: str
    value: str | int | float


class ParamFieldDef(BaseModel):
    key: str
    label: str
    type: Literal["number", "select"]
    default: int | float | str = 0
    min: int | float | None = None
    max: int | float | None = None
    step: int | float | None = None
    options: list[SelectOption] | None = None


class CustomFilterCreate(CamelModel):
    nm: str = Field(..., description="커스텀 필터 이름")
    description: str = Field("", description="필터 설명")
    code: str = Field(..., description="Python 필터 코드")
    params: list[ParamFieldDef] = Field(
        default_factory=list,
        description="파라미터 정의 (ParamFieldDef 배열)",
    )


class CustomFilterUpdate(CamelModel):
    nm: str | None = Field(None, description="커스텀 필터 이름")
    description: str | None = Field(None, description="필터 설명")
    code: str | None = Field(None, description="Python 필터 코드")
    params: list[ParamFieldDef] | None = Field(None, description="파라미터 정의 (ParamFieldDef 배열)")


class CustomFilterResponse(CamelModel):
    id: int = Field(..., description="커스텀 필터 ID")
    nm: str = Field(..., description="커스텀 필터 이름")
    description: str = Field("", description="필터 설명")
    code: str = Field(..., description="Python 필터 코드")
    params: list[ParamFieldDef] = Field(default_factory=list, description="파라미터 정의 (ParamFieldDef 배열)")
    version: int = Field(..., description="코드 버전")
    created_at: datetime = Field(..., description="생성 일시")
    updated_at: datetime = Field(..., description="수정 일시")


class CustomFilterListResponse(CamelModel):
    items: list[CustomFilterResponse] = Field(..., description="커스텀 필터 목록")
