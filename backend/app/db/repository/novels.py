"""Novel / Chapter repository — DB ↔ Pydantic conversions."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.tables import ChapterTable, NovelTable
from app.models.novel import Chapter, Novel


async def save_novel(session: AsyncSession, novel: Novel) -> None:
    """Insert a novel and its chapters into the database."""
    row = NovelTable(
        id=novel.id,
        title=novel.title,
        filename=novel.filename,
        created_at=novel.created_at,
    )
    for ch in novel.chapters:
        row.chapters.append(
            ChapterTable(
                id=ch.id,
                index=ch.index,
                title=ch.title,
                content=ch.content,
                word_count=ch.word_count,
            )
        )
    session.add(row)
    await session.commit()


async def get_novel(session: AsyncSession, novel_id: str) -> Novel | None:
    """Fetch a novel with its chapters, or None if not found."""
    stmt = select(NovelTable).where(NovelTable.id == novel_id)
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    if row is None:
        return None
    return _novel_from_row(row)


def _novel_from_row(row: NovelTable) -> Novel:
    """Convert an ORM row into a Pydantic Novel model."""
    return Novel(
        id=row.id,
        title=row.title,
        filename=row.filename,
        created_at=row.created_at,
        chapters=[
            Chapter(
                id=ch.id,
                index=ch.index,
                title=ch.title,
                content=ch.content,
                word_count=ch.word_count,
            )
            for ch in row.chapters
        ],
    )
