"""R2 (Reader-Rewriter) — Pydantic data models."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.screenplay import Scene


class R2ScanRequest(BaseModel):
    """Request body for starting an R2 scan."""

    novel_id: str

    model_config = ConfigDict(extra="forbid")


class R2ScanResult(BaseModel):
    """Result of an R2 sliding-window scan over a novel."""

    id: str
    novel_id: str
    scenes: list[Scene] = Field(default_factory=list)
    window_count: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = ConfigDict(extra="forbid")
