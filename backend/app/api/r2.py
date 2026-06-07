"""R2 (Reader-Rewriter) API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.r2 import R2ScanRequest, R2ScanResult
from app.services import novel_service, r2_service

router = APIRouter(prefix="/r2", tags=["r2"])


@router.post("/scan")
async def scan_novel(body: R2ScanRequest) -> R2ScanResult:
    """Run an R2 sliding-window scan on a novel."""
    novel = await novel_service.get_novel(body.novel_id)
    if novel is None:
        raise HTTPException(status_code=404, detail="Novel not found")
    return await r2_service.scan_novel(novel)


@router.get("/{novel_id}/result")
async def get_scan_result(novel_id: str) -> R2ScanResult:
    """Get the R2 scan result for a novel."""
    scan = await r2_service.get_scan(novel_id)
    if scan is None:
        raise HTTPException(status_code=404, detail="R2 scan not found")
    return scan
