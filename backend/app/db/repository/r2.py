"""R2 scan persistence — save and retrieve sliding-window scan results."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.tables import R2ScanTable, R2SceneElementTable, R2SceneTable
from app.models.r2 import R2ScanResult
from app.models.screenplay import Scene, SceneElement


async def save_scan(session: AsyncSession, scan: R2ScanResult) -> None:
    """Save an R2 scan and all its scenes to the database."""
    scan_row = R2ScanTable(
        id=scan.id,
        novel_id=scan.novel_id,
        window_count=scan.window_count,
        created_at=scan.created_at,
    )
    session.add(scan_row)

    for scene in scan.scenes:
        scene_id = str(uuid.uuid4())
        scene_row = R2SceneTable(
            id=scene_id,
            scan_id=scan.id,
            index=scene.index,
            setting=scene.setting,
            location=scene.location,
            time_of_day=scene.time_of_day,
            source_chapter=scene.source_chapter,
            source_window=0,
            characters=scene.characters,
        )
        session.add(scene_row)

        for pos, elem in enumerate(scene.elements):
            session.add(
                R2SceneElementTable(
                    id=str(uuid.uuid4()),
                    scene_id=scene_id,
                    type=elem.type,
                    content=elem.content,
                    character=elem.character,
                    position=pos,
                )
            )

    await session.commit()


async def get_scan_by_novel(session: AsyncSession, novel_id: str) -> R2ScanResult | None:
    """Get the R2 scan result for a given novel ID."""
    result = await session.execute(
        select(R2ScanTable)
        .where(R2ScanTable.novel_id == novel_id)
        .options(selectinload(R2ScanTable.scenes).selectinload(R2SceneTable.elements))
    )
    row = result.scalar_one_or_none()
    if row is None:
        return None
    return _scan_from_row(row)


def _scan_from_row(row: R2ScanTable) -> R2ScanResult:
    """Convert an ORM row to a Pydantic model."""
    return R2ScanResult(
        id=row.id,
        novel_id=row.novel_id,
        window_count=row.window_count,
        created_at=row.created_at,
        scenes=[
            Scene(
                index=scene_row.index,
                setting=scene_row.setting,
                location=scene_row.location,
                time_of_day=scene_row.time_of_day,
                source_chapter=scene_row.source_chapter,
                characters=scene_row.characters,
                elements=[
                    SceneElement(
                        type=elem.type,  # type: ignore[arg-type]
                        content=elem.content,
                        character=elem.character,
                    )
                    for elem in scene_row.elements
                ],
            )
            for scene_row in row.scenes
        ],
    )
