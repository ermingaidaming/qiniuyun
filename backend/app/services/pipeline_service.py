"""Pipeline orchestrator — chains CPC → R2 → HAR → ScreenYAML in sequence.

Each step is guarded by try/except so a failure at any stage reports exactly
which step failed, while earlier completed steps are preserved (all services
are idempotent — re-running the pipeline skips already-completed work).
"""

from __future__ import annotations

from app.core.config import settings
from app.db.engine import async_session
from app.db.repository.screenplays import replace_screenplay as _replace_screenplay
from app.models.pipeline import PipelineRunResult, PipelineStep, StepStatus
from app.models.screenplay import Screenplay
from app.services import cpc_service, har_service, novel_service, r2_service
from app.services.screenplay_service import get_screenplay_by_novel
from app.services.screenyaml import screenyaml_dumps


async def run_pipeline(novel_id: str) -> PipelineRunResult:
    """Execute the full pipeline for a novel.

    Steps:
      1. CPC — build causal plot graph
      2. R2 — sliding-window rewrite
      3. HAR — hallucination detection & correction
      4. ScreenYAML — serialize final screenplay to YAML

    Returns a PipelineRunResult with per-step status.  On partial failure the
    caller can re-submit the same novel_id; idempotent services skip already-
    completed work.
    """
    # ── Load novel ───────────────────────────────────────────────────
    novel = await novel_service.get_novel(novel_id)
    if novel is None:
        raise ValueError("Novel not found")

    steps: list[PipelineStep] = []

    # ── Step 1: CPC ──────────────────────────────────────────────────
    try:
        await cpc_service.build_causal_graph(novel)
        steps.append(PipelineStep(name="cpc", status=StepStatus.completed))
    except Exception as exc:
        steps.append(PipelineStep(name="cpc", status=StepStatus.failed, error=str(exc)))
        return _partial(novel_id, steps)

    # ── Step 2: R2 ───────────────────────────────────────────────────
    try:
        scan_result = await r2_service.scan_novel(novel)
        steps.append(PipelineStep(name="r2", status=StepStatus.completed))

        # Save R2 scenes as Screenplay so HAR can consume them
        screenplay = Screenplay(
            novel_id=novel.id,
            title=f"《{novel.title}》剧本",
            source_novel=novel.title,
            total_chapters=len(novel.chapters),
            generated_by=settings.llm_model if settings.llm_api_key else "r2",
            scenes=scan_result.scenes,
        )
        async with async_session() as session:
            await _replace_screenplay(session, screenplay)
    except Exception as exc:
        steps.append(PipelineStep(name="r2", status=StepStatus.failed, error=str(exc)))
        return _partial(novel_id, steps)

    # ── Step 3: HAR ──────────────────────────────────────────────────
    try:
        har_report = await har_service.refine(novel)
        steps.append(PipelineStep(name="har", status=StepStatus.completed))

        # Write HAR-corrected scenes back to Screenplay
        screenplay.scenes = har_report.corrected_scenes
        async with async_session() as session:
            await _replace_screenplay(session, screenplay)
    except Exception as exc:
        steps.append(PipelineStep(name="har", status=StepStatus.failed, error=str(exc)))
        return _partial(novel_id, steps)

    # ── Step 4: ScreenYAML ───────────────────────────────────────────
    try:
        final_screenplay = await get_screenplay_by_novel(novel_id)
        if final_screenplay is None:
            raise ValueError("Screenplay not found after HAR — this should not happen")
        yaml_str = screenyaml_dumps(final_screenplay)
        steps.append(PipelineStep(name="screenyaml", status=StepStatus.completed))
    except Exception as exc:
        steps.append(PipelineStep(name="screenyaml", status=StepStatus.failed, error=str(exc)))
        return _partial(novel_id, steps)

    return PipelineRunResult(
        novel_id=novel_id,
        status="completed",
        steps=steps,
        screenyaml=yaml_str,
        screenplay_id=final_screenplay.id,
    )


def _partial(novel_id: str, steps: list[PipelineStep]) -> PipelineRunResult:
    """Build a partial-failure result."""
    return PipelineRunResult(novel_id=novel_id, status="partial", steps=steps)
