"""Screenplay / Scene / SceneElement repository — DB ↔ Pydantic conversions."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.tables import SceneElementTable, SceneTable, ScreenplayTable
from app.models.screenplay import Scene, SceneElement, Screenplay


async def save_screenplay(session: AsyncSession, screenplay: Screenplay) -> None:
    """Insert a screenplay with all scenes and elements into the database."""
    row = ScreenplayTable(
        id=screenplay.id,
        novel_id=screenplay.novel_id,
        title=screenplay.title,
        source_novel=screenplay.source_novel,
        novel_author=screenplay.novel_author,
        total_chapters=screenplay.total_chapters,
        generated_by=screenplay.generated_by,
    )
    for scene in screenplay.scenes:
        scene_row = SceneTable(
            id=_scene_id(screenplay.id, scene.index),
            index=scene.index,
            setting=scene.setting,
            location=scene.location,
            time_of_day=scene.time_of_day,
            source_chapter=scene.source_chapter,
            characters=scene.characters,
        )
        for i, elem in enumerate(scene.elements):
            scene_row.elements.append(
                SceneElementTable(
                    id=_element_id(screenplay.id, scene.index, i),
                    type=elem.type,
                    content=elem.content,
                    character=elem.character,
                    position=i,
                )
            )
        row.scenes.append(scene_row)
    session.add(row)
    await session.commit()


async def get_screenplay(session: AsyncSession, screenplay_id: str) -> Screenplay | None:
    """Fetch a screenplay with all scenes and elements."""
    stmt = select(ScreenplayTable).where(ScreenplayTable.id == screenplay_id)
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    if row is None:
        return None
    return _screenplay_from_row(row)


async def get_screenplay_by_novel(session: AsyncSession, novel_id: str) -> Screenplay | None:
    """Find the screenplay for a given novel, or None."""
    stmt = select(ScreenplayTable).where(ScreenplayTable.novel_id == novel_id)
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    if row is None:
        return None
    return _screenplay_from_row(row)


def _screenplay_from_row(row: ScreenplayTable) -> Screenplay:
    """Convert an ORM row into a Pydantic Screenplay model."""
    return Screenplay(
        id=row.id,
        novel_id=row.novel_id,
        title=row.title,
        source_novel=row.source_novel,
        novel_author=row.novel_author,
        total_chapters=row.total_chapters,
        generated_by=row.generated_by,
        scenes=[
            Scene(
                index=s.index,
                setting=s.setting,
                location=s.location,
                time_of_day=s.time_of_day,
                source_chapter=s.source_chapter,
                characters=s.characters,
                elements=[
                    SceneElement(
                        type=e.type,  # type: ignore[arg-type]
                        content=e.content,
                        character=e.character,
                    )
                    for e in s.elements
                ],
            )
            for s in row.scenes
        ],
    )


# Scene / Element IDs are deterministic so the same generate request
# produces the same database rows (idempotent with ON CONFLICT).
def _scene_id(screenplay_id: str, index: int) -> str:
    return f"{screenplay_id}-s{index}"


def _element_id(screenplay_id: str, scene_index: int, elem_index: int) -> str:
    return f"{screenplay_id}-s{scene_index}-e{elem_index}"
