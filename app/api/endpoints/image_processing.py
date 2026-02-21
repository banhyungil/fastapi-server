from fastapi import APIRouter, File, Form, UploadFile

router = APIRouter()


@router.post("/image-processing", tags=["img-processing"])
async def img_processing(
    file: UploadFile = File(...),
    prc_type: str = Form(..., alias="prcType"),
) -> dict[str, str | int]:
    uploaded_file_name = file.filename or ""
    uploaded_file_type = file.content_type or ""
    uploaded_file_bytes = await file.read()
    uploaded_file_size = len(uploaded_file_bytes)

    return {
        "message": "request parsed",
        "prcType": prc_type,
        "fileName": uploaded_file_name,
        "contentType": uploaded_file_type,
        "fileSize": uploaded_file_size,
    }
