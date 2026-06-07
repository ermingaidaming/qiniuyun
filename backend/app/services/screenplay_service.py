from __future__ import annotations

from app.core.config import settings
from app.db.engine import async_session
from app.db.repository.screenplays import get_screenplay as _db_get_screenplay
from app.db.repository.screenplays import get_screenplay_by_novel as _db_get_screenplay_by_novel
from app.db.repository.screenplays import save_screenplay as _db_save_screenplay
from app.models.novel import Novel
from app.models.screenplay import Scene, SceneElement, Screenplay
from app.services.llm_service import convert_chapter_to_scene


async def generate_screenplay(novel: Novel) -> Screenplay:
    """Generate a screenplay from a parsed novel.

    Converts each chapter using the LLM and merges all scenes.
    """
    all_scenes: list[Scene] = []
    scene_index = 0

    for chapter in novel.chapters:
        try:
            raw_scenes = await convert_chapter_to_scene(chapter.title, chapter.content)
            for raw in raw_scenes:
                scene_index += 1
                elements = [
                    SceneElement(
                        type=elem.get("type", "action"),
                        content=elem.get("content", ""),
                        character=elem.get("character"),
                    )
                    for elem in raw.get("elements", [])
                ]
                all_scenes.append(
                    Scene(
                        index=scene_index,
                        setting=raw.get("setting", chapter.title),
                        location=raw.get("location", ""),
                        time_of_day=raw.get("time", ""),
                        source_chapter=chapter.index,
                        characters=raw.get("characters", []),
                        elements=elements,
                    )
                )
        except Exception as exc:
            # If LLM fails for a chapter, add an error placeholder scene
            scene_index += 1
            all_scenes.append(
                Scene(
                    index=scene_index,
                    setting=f"第{chapter.index}章（生成失败）",
                    elements=[SceneElement(type="action", content=f"本章生成出错: {exc}")],
                )
            )

    screenplay = Screenplay(
        novel_id=novel.id,
        title=f"《{novel.title}》剧本",
        source_novel=novel.title,
        total_chapters=len(novel.chapters),
        generated_by=settings.llm_model if settings.llm_api_key else "mock",
        scenes=all_scenes,
    )
    async with async_session() as session:
        await _db_save_screenplay(session, screenplay)
    return screenplay


async def get_screenplay(screenplay_id: str) -> Screenplay | None:
    """Get a screenplay by ID."""
    async with async_session() as session:
        return await _db_get_screenplay(session, screenplay_id)


async def get_screenplay_by_novel(novel_id: str) -> Screenplay | None:
    """Get the screenplay for a given novel ID."""
    async with async_session() as session:
        return await _db_get_screenplay_by_novel(session, novel_id)
