from __future__ import annotations

import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field


class Chapter(BaseModel):
    """A parsed chapter from an uploaded novel."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    index: int
    title: str = ""
    content: str
    word_count: int = 0

    model_config = ConfigDict(extra="forbid")


class Novel(BaseModel):
    """An uploaded novel with parsed chapters."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    filename: str
    chapters: list[Chapter] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = ConfigDict(extra="forbid")


class NovelDetail(Novel):
    """Full novel detail including chapter content."""

    pass
