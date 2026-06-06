from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SceneElementType = Literal["action", "character", "dialogue", "parenthetical"]


class SceneElement(BaseModel):
    """A single element in a scene: action, character heading, dialogue, or parenthetical."""

    type: SceneElementType
    content: str
    character: str | None = None

    model_config = ConfigDict(extra="forbid")


class Scene(BaseModel):
    """A single scene in the screenplay."""

    index: int
    setting: str = ""
    location: str = ""
    time_of_day: str = ""
    source_chapter: int = 0
    characters: list[str] = Field(default_factory=list)
    elements: list[SceneElement] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class Screenplay(BaseModel):
    """A generated screenplay."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    novel_id: str
    title: str
    source_novel: str = ""
    novel_author: str = ""
    total_chapters: int = 0
    generated_by: str = ""
    scenes: list[Scene] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")
