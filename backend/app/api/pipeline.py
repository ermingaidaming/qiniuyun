"""Pipeline API routes — full CPC → R2 → HAR → ScreenYAML chain."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.pipeline import PipelineRunRequest, PipelineRunResult
from app.services import pipeline_service

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


@router.post("/run")
async def run_pipeline(body: PipelineRunRequest) -> PipelineRunResult:
    """Execute the full AI pipeline for a novel.

    1. CPC — causal plot graph
    2. R2 — sliding-window rewrite
    3. HAR — hallucination-aware refinement
    4. ScreenYAML — structured screenplay output

    Each step is idempotent — re-running safely skips completed work.
    On partial failure, completed steps are preserved and only the failed
    step needs to be retried.
    """
    try:
        return await pipeline_service.run_pipeline(body.novel_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Novel not found") from None
