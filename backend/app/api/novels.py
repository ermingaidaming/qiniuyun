from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.core.config import settings
from app.models.novel import Novel
from app.services import novel_service

router = APIRouter(tags=["novels"])


@router.post("/novels/upload")
async def upload_novel(file: UploadFile = File(...)) -> Novel:  # noqa: B008
    """Upload a TXT novel file, parse its chapters, and return the novel metadata."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    # Validate file type
    if not file.filename.lower().endswith(".txt"):
        raise HTTPException(status_code=400, detail="Only .txt files are supported")

    # Read content
    raw = await file.read()
    if len(raw) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {settings.max_upload_size_bytes // 1024}KB",
        )

    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError:
        try:
            content = raw.decode("gbk")
        except UnicodeDecodeError as err:
            raise HTTPException(status_code=400, detail="Cannot decode file. Use UTF-8 or GBK encoding.") from err

    novel = await novel_service.parse_novel(file.filename, content)
    return novel


@router.get("/novels/{novel_id}")
async def get_novel(novel_id: str) -> Novel:
    """Get novel detail by ID."""
    novel = await novel_service.get_novel(novel_id)
    if novel is None:
        raise HTTPException(status_code=404, detail="Novel not found")
    return novel
