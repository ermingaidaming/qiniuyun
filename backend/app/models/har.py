"""HAR (Hallucination-Aware Refinement) — Pydantic data models."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.screenplay import Scene

Severity = Literal["critical", "major", "minor"]
Category = Literal["character", "event", "dialogue", "setting", "detail"]


class HARFinding(BaseModel):
    """A single hallucination finding in a screenplay scene."""

    scene_index: int
    severity: Severity
    category: Category
    description: str
    hallucinated_text: str = ""
    suggested_fix: str = ""
    source_evidence: str = ""

    model_config = ConfigDict(extra="forbid")


class HARReport(BaseModel):
    """Result of a HAR hallucination detection and correction pass."""

    id: str
    novel_id: str
    total_scenes: int = 0
    total_findings: int = 0
    findings: list[HARFinding] = Field(default_factory=list)
    corrected_scenes: list[Scene] = Field(default_factory=list)
    verification_rounds: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = ConfigDict(extra="forbid")


class HARRefineRequest(BaseModel):
    """Request body for running HAR refinement."""

    novel_id: str

    model_config = ConfigDict(extra="forbid")
