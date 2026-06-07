"""SQLAlchemy ORM table definitions.

Maps to Pydantic models in app/models/. Table rows → Pydantic instances
happens in the repository layer, not here.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class NovelTable(Base):
    __tablename__ = "novels"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    filename: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime)

    chapters: Mapped[list[ChapterTable]] = relationship(
        "ChapterTable", back_populates="novel", cascade="all, delete-orphan", lazy="selectin"
    )
    screenplay: Mapped[ScreenplayTable | None] = relationship(
        "ScreenplayTable", back_populates="novel", cascade="all, delete-orphan", uselist=False, lazy="selectin"
    )


class ChapterTable(Base):
    __tablename__ = "chapters"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    novel_id: Mapped[str] = mapped_column(String(36), ForeignKey("novels.id"), nullable=False)
    index: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(200), default="")
    content: Mapped[str] = mapped_column(String)
    word_count: Mapped[int] = mapped_column(Integer, default=0)

    novel: Mapped[NovelTable] = relationship("NovelTable", back_populates="chapters")


class ScreenplayTable(Base):
    __tablename__ = "screenplays"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    novel_id: Mapped[str] = mapped_column(String(36), ForeignKey("novels.id"), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200))
    source_novel: Mapped[str] = mapped_column(String(200), default="")
    novel_author: Mapped[str] = mapped_column(String(100), default="")
    total_chapters: Mapped[int] = mapped_column(Integer, default=0)
    generated_by: Mapped[str] = mapped_column(String(100), default="")

    novel: Mapped[NovelTable] = relationship("NovelTable", back_populates="screenplay")
    scenes: Mapped[list[SceneTable]] = relationship(
        "SceneTable", back_populates="screenplay", cascade="all, delete-orphan", lazy="selectin"
    )


class SceneTable(Base):
    __tablename__ = "scenes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    screenplay_id: Mapped[str] = mapped_column(String(36), ForeignKey("screenplays.id"), nullable=False)
    index: Mapped[int] = mapped_column(Integer)
    setting: Mapped[str] = mapped_column(String(500), default="")
    location: Mapped[str] = mapped_column(String(200), default="")
    time_of_day: Mapped[str] = mapped_column(String(50), default="")
    source_chapter: Mapped[int] = mapped_column(Integer, default=0)
    characters: Mapped[list[str]] = mapped_column(JSON, default=list)

    screenplay: Mapped[ScreenplayTable] = relationship("ScreenplayTable", back_populates="scenes")
    elements: Mapped[list[SceneElementTable]] = relationship(
        "SceneElementTable",
        back_populates="scene",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="SceneElementTable.position",
    )


class SceneElementTable(Base):
    __tablename__ = "scene_elements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    scene_id: Mapped[str] = mapped_column(String(36), ForeignKey("scenes.id"), nullable=False)
    type: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(String)
    character: Mapped[str | None] = mapped_column(String(100), nullable=True)
    position: Mapped[int] = mapped_column(Integer, default=0)

    scene: Mapped[SceneTable] = relationship("SceneTable", back_populates="elements")


class CausalGraphTable(Base):
    __tablename__ = "cpc_graphs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    novel_id: Mapped[str] = mapped_column(String(36), ForeignKey("novels.id"), unique=True, nullable=False)
    dag_valid: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)

    novel: Mapped[NovelTable] = relationship("NovelTable")
    events: Mapped[list[EventTable]] = relationship(
        "EventTable", back_populates="graph", cascade="all, delete-orphan", lazy="selectin"
    )
    relations: Mapped[list[CausalRelationTable]] = relationship(
        "CausalRelationTable", back_populates="graph", cascade="all, delete-orphan", lazy="selectin"
    )


class EventTable(Base):
    __tablename__ = "cpc_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    graph_id: Mapped[str] = mapped_column(String(36), ForeignKey("cpc_graphs.id"), nullable=False)
    index: Mapped[int] = mapped_column(Integer)
    chapter_index: Mapped[int] = mapped_column(Integer)
    description: Mapped[str] = mapped_column(String)
    characters: Mapped[list[str]] = mapped_column(JSON, default=list)
    location: Mapped[str] = mapped_column(String(200), default="")
    time: Mapped[str] = mapped_column(String(100), default="")

    graph: Mapped[CausalGraphTable] = relationship("CausalGraphTable", back_populates="events")


class CausalRelationTable(Base):
    __tablename__ = "cpc_relations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    graph_id: Mapped[str] = mapped_column(String(36), ForeignKey("cpc_graphs.id"), nullable=False)
    source_event_id: Mapped[str] = mapped_column(String(36), nullable=False)
    target_event_id: Mapped[str] = mapped_column(String(36), nullable=False)
    relation_type: Mapped[str] = mapped_column(String(20))
    confidence: Mapped[float] = mapped_column(default=1.0)

    graph: Mapped[CausalGraphTable] = relationship("CausalGraphTable", back_populates="relations")


class R2ScanTable(Base):
    __tablename__ = "r2_scans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    novel_id: Mapped[str] = mapped_column(String(36), ForeignKey("novels.id"), unique=True, nullable=False)
    window_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime)

    novel: Mapped[NovelTable] = relationship("NovelTable")
    scenes: Mapped[list[R2SceneTable]] = relationship(
        "R2SceneTable", back_populates="scan", cascade="all, delete-orphan", lazy="selectin"
    )


class R2SceneTable(Base):
    __tablename__ = "r2_scenes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    scan_id: Mapped[str] = mapped_column(String(36), ForeignKey("r2_scans.id"), nullable=False)
    index: Mapped[int] = mapped_column(Integer)
    setting: Mapped[str] = mapped_column(String(500), default="")
    location: Mapped[str] = mapped_column(String(200), default="")
    time_of_day: Mapped[str] = mapped_column(String(50), default="")
    source_chapter: Mapped[int] = mapped_column(Integer, default=0)
    source_window: Mapped[int] = mapped_column(Integer, default=0)
    characters: Mapped[list[str]] = mapped_column(JSON, default=list)

    scan: Mapped[R2ScanTable] = relationship("R2ScanTable", back_populates="scenes")
    elements: Mapped[list[R2SceneElementTable]] = relationship(
        "R2SceneElementTable",
        back_populates="scene",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="R2SceneElementTable.position",
    )


class R2SceneElementTable(Base):
    __tablename__ = "r2_scene_elements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    scene_id: Mapped[str] = mapped_column(String(36), ForeignKey("r2_scenes.id"), nullable=False)
    type: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(String)
    character: Mapped[str | None] = mapped_column(String(100), nullable=True)
    position: Mapped[int] = mapped_column(Integer, default=0)

    scene: Mapped[R2SceneTable] = relationship("R2SceneTable", back_populates="elements")
