"""HAR (Hallucination-Aware Refinement) API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.har import HARRefineRequest, HARReport
from app.services import har_service, novel_service

router = APIRouter(prefix="/har", tags=["har"])


@router.post("/refine")
async def refine_screenplay(body: HARRefineRequest) -> HARReport:
    """Run HAR hallucination detection and self-correction on a screenplay."""
    novel = await novel_service.get_novel(body.novel_id)
    if novel is None:
        raise HTTPException(status_code=404, detail="Novel not found")
    return await har_service.refine(novel)


@router.get("/{novel_id}/report")
async def get_har_report(novel_id: str) -> HARReport:
    """Get the HAR refinement report for a novel."""
    report = await har_service.get_report(novel_id)
    if report is None:
        raise HTTPException(status_code=404, detail="HAR report not found")
    return report
