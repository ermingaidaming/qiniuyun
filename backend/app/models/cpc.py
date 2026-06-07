"""CPC (Causal Plot Graph) — Pydantic data models."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

RelationType = Literal["causes", "before", "references"]


class Event(BaseModel):
    """A single event extracted from a novel chapter."""

    id: str
    index: int  # global order within the novel
    chapter_index: int
    description: str
    characters: list[str] = Field(default_factory=list)
    location: str = ""
    time: str = ""

    model_config = ConfigDict(extra="forbid")


class CausalRelation(BaseModel):
    """A directed relationship between two events."""

    id: str
    source_event_id: str
    target_event_id: str
    relation_type: RelationType
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

    model_config = ConfigDict(extra="forbid")


class CausalGraph(BaseModel):
    """A directed acyclic graph of events and their causal relationships."""

    id: str
    novel_id: str
    events: list[Event] = Field(default_factory=list)
    relations: list[CausalRelation] = Field(default_factory=list)
    dag_valid: bool = True  # False if cycles were removed
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = ConfigDict(extra="forbid")


class BuildCpcRequest(BaseModel):
    """Request body for building a CPC graph."""

    novel_id: str

    model_config = ConfigDict(extra="forbid")
