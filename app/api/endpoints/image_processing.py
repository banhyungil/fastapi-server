# 외부 패키지는 패키지명으로 import
from io import BytesIO
from pathlib import Path
from uuid import uuid4
from datetime import datetime
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

# 절대 import
from app.services.image_processing_service import process_image

router = APIRouter()


@router.post("/image-processing", tags=["img-processing"])
async def img_processing(
    file: UploadFile = File(...),
    prc_type: str = Form(..., alias="prcType"),
) -> StreamingResponse:
    uploaded_file_bytes = await file.read()

    try:
        processed_image_bytes = process_image(prc_type=prc_type, image_bytes=uploaded_file_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return StreamingResponse(BytesIO(processed_image_bytes), media_type="image/png")


@router.post("/image-processing/save", tags=["img-processing"])
async def img_processing_save(file: UploadFile = File(...)) -> dict[str, Any]:
    # Python: 연산자 오버로딩
    # Path / "문자열"이면 Path.__truediv__()가 호출되어 경로 결합 연산자로 작동
    base = Path("uploads") / datetime.now().strftime("%Y-%m-%d")
    base.mkdir(parents=True, exist_ok=True)

    data = await file.read()
    if file.content_type not in ("image/png", "image/jpeg"):
        raise HTTPException(400, "unsupported content type")
    
    ext = ".png" if file.content_type == "image/png" else ".jpg"
    name = f"{uuid4().hex}{ext}"
    saved = base / name
    saved.write_bytes(data)
