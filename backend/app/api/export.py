from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from app.services import export_service, screenplay_service

router = APIRouter(tags=["export"])


def _make_filename(title: str, ext: str) -> str:
    """Build a safe filename, handling Chinese characters."""
    safe_title = title.replace("/", "_").replace("\\", "_")
    return f"{safe_title}.{ext}"


def _content_disposition(filename: str) -> str:
    """Build Content-Disposition header with proper encoding for non-ASCII filenames."""
    encoded = quote(filename, safe="")
    # Use RFC 5987 encoding only — Starlette headers must be ASCII-safe
    return f"attachment; filename*=UTF-8''{encoded}"


@router.get("/export/{screenplay_id}")
async def export_screenplay(
    screenplay_id: str,
    format: str = Query("txt", pattern="^(txt|docx|yaml)$"),
):
    """Export a screenplay as TXT or DOCX file."""
    screenplay = await screenplay_service.get_screenplay(screenplay_id)
    if screenplay is None:
        raise HTTPException(status_code=404, detail="Screenplay not found")

    if format == "yaml":
        content = export_service.export_yaml(screenplay)
        media_type = "application/x-yaml; charset=utf-8"
        ext = "yaml"
    elif format == "docx":
        content = export_service.export_docx(screenplay)
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ext = "docx"
    else:
        content = export_service.export_txt(screenplay)
        media_type = "text/plain; charset=utf-8"
        ext = "txt"

    filename = _make_filename(screenplay.title, ext)
    disposition = _content_disposition(filename)

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": disposition},
    )
