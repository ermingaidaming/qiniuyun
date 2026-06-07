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
