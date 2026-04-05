from pydantic import Field

from app.schemas.files_schema import CamelModel, FileUploadResponse


class LocalScanRequest(CamelModel):
    dir_path: str = Field(..., description="스캔할 디렉토리 절대 경로")
    recursive: bool = Field(False, description="하위 디렉토리 포함 여부")
    use_thumbnail: bool = Field(True, description="썸네일 생성 여부")


class LocalFileInfo(CamelModel):
    path: str = Field(..., description="파일 절대 경로")
    file_name: str = Field(..., description="파일명")
    mime_type: str = Field(..., description="MIME 타입")
    size_bytes: int = Field(..., ge=0, description="파일 크기 (bytes)")
    width: int = Field(0, description="이미지 가로 해상도 (px)")
    height: int = Field(0, description="이미지 세로 해상도 (px)")
    thumbnail_url: str = Field("", description="base64 썸네일 data URL")
    already_registered: bool = Field(False, description="이미 등록된 파일 여부")


class LocalScanResponse(CamelModel):
    items: list[LocalFileInfo] = Field(..., description="스캔된 파일 목록")


class LocalRegisterFileItem(CamelModel):
    path: str = Field(..., description="등록할 파일 절대 경로")


class LocalRegisterRequest(CamelModel):
    files: list[LocalRegisterFileItem] = Field(..., min_length=1, description="등록할 파일 목록")


class LocalRegisterResponse(CamelModel):
    items: list[FileUploadResponse] = Field(..., description="등록된 파일 목록")
