"""Pipeline orchestration models — CPC → R2 → HAR → ScreenYAML chain."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict


class StepStatus(str, Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"


class PipelineStep(BaseModel):
    """Single step result within a pipeline run."""

    name: str  # "cpc" | "r2" | "har" | "screenyaml"
    status: StepStatus
    error: str | None = None


class PipelineRunRequest(BaseModel):
    """Request to execute the full pipeline."""

    model_config = ConfigDict(extra="forbid")

    novel_id: str


class PipelineRunResult(BaseModel):
    """Result of a pipeline run — each step is reported individually."""

    model_config = ConfigDict(extra="forbid")

    novel_id: str
    status: str  # "completed" | "partial"
    steps: list[PipelineStep]
    screenyaml: str | None = None
    screenplay_id: str | None = None
