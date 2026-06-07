"""R2 (Reader-Rewriter) service — sliding-window novel scanning and rewriting.

Pipeline:
  chapters → sliding-window chunking → per-window LLM rewrite → dedup merge → R2ScanResult
"""

from __future__ import annotations

import uuid
from typing import Any

from app.core.config import settings
from app.db.engine import async_session
from app.db.repository.r2 import get_scan_by_novel as _db_get_scan
from app.db.repository.r2 import save_scan as _db_save_scan
from app.models.novel import Novel
from app.models.r2 import R2ScanResult
from app.models.screenplay import Scene, SceneElement
from app.services.llm_service import SYSTEM_PROMPT, _call_llm, _parse_llm_json

# ── R2-specific prompt ────────────────────────────────────────────────

R2_USER_TEMPLATE = """请将以下小说文本片段转化为剧本格式。

注意：这段文字是从长篇小说中截取的一个片段，可能开头或结尾处存在不完整的场景。
请只生成片段中完整可辨认的场景，不要凭空补充上下文。

## 文本片段

{window_content}
"""

# ── Public API ────────────────────────────────────────────────────────


async def scan_novel(novel: Novel) -> R2ScanResult:
    """Run R2 sliding-window scan on a novel.

    1. Split novel text into overlapping windows
    2. Rewrite each window into screenplay scenes via LLM
    3. Deduplicate overlapping scenes across adjacent windows
    4. Persist and return
    """
    # Idempotent: return existing scan if already done
    async with async_session() as session:
        existing = await _db_get_scan(session, novel.id)
        if existing is not None:
            return existing

    # ── 1. Build sliding windows ───────────────────────────────────
    windows = _build_windows(
        novel.chapters,
        window_size=settings.r2_window_size,
        overlap=settings.r2_overlap_size,
    )

    if not windows:
        scan = R2ScanResult(
            id=str(uuid.uuid4()),
            novel_id=novel.id,
            scenes=[],
            window_count=0,
        )
        async with async_session() as session:
            await _db_save_scan(session, scan)
        return scan

    # ── 2. Rewrite each window ────────────────────────────────────
    all_scenes: list[tuple[int, Scene]] = []  # (window_index, scene)
    scene_counter = 0

    for win in windows:
        try:
            raw = await _call_llm(
                SYSTEM_PROMPT,
                R2_USER_TEMPLATE.format(window_content=win["text"]),
            )
            raw_scenes = _parse_llm_json(raw)
            for raw_scene in raw_scenes:
                scene_counter += 1
                elements = [
                    SceneElement(
                        type=elem.get("type", "action"),
                        content=elem.get("content", ""),
                        character=elem.get("character"),
                    )
                    for elem in raw_scene.get("elements", [])
                ]
                all_scenes.append(
                    (
                        win["index"],
                        Scene(
                            index=scene_counter,
                            setting=raw_scene.get("setting", f"窗口 {win['index'] + 1}"),
                            elements=elements,
                        ),
                    )
                )
        except Exception:
            # If a window fails, add a placeholder scene and continue
            scene_counter += 1
            all_scenes.append(
                (
                    win["index"],
                    Scene(
                        index=scene_counter,
                        setting=f"窗口 {win['index'] + 1}（处理失败）",
                        elements=[SceneElement(type="action", content="此窗口处理出错，已跳过。")],
                    ),
                )
            )

    # ── 3. Deduplicate overlapping scenes ─────────────────────────
    scenes = _deduplicate_scenes([s for _, s in all_scenes])

    # Re-index after dedup
    for i, scene in enumerate(scenes):
        scene.index = i + 1

    # ── 4. Persist ────────────────────────────────────────────────
    scan = R2ScanResult(
        id=str(uuid.uuid4()),
        novel_id=novel.id,
        scenes=scenes,
        window_count=len(windows),
    )
    async with async_session() as session:
        await _db_save_scan(session, scan)

    return scan


async def get_scan(novel_id: str) -> R2ScanResult | None:
    """Get the R2 scan result for a novel, or None if not yet scanned."""
    async with async_session() as session:
        return await _db_get_scan(session, novel_id)


# ── Sliding Window ────────────────────────────────────────────────────


def _build_windows(
    chapters: list[Any],
    window_size: int,
    overlap: int,
) -> list[dict[str, Any]]:
    """Build overlapping sliding windows from chapter texts.

    Returns a list of dicts with keys: index, text.
    """
    # Concatenate all chapter texts with separators
    parts: list[str] = []
    for ch in chapters:
        parts.append(ch.content)
    full_text = "\n\n".join(parts).strip()

    if not full_text:
        return []

    # Short text: use a single window
    if len(full_text) <= window_size:
        return [{"index": 0, "text": full_text}]

    step = max(window_size - overlap, 1)  # ensure positive step
    windows: list[dict[str, Any]] = []
    pos = 0
    win_idx = 0

    while pos < len(full_text):
        window_text = full_text[pos : pos + window_size]
        # Skip tiny trailing windows
        if len(window_text.strip()) < 100:
            break
        windows.append({"index": win_idx, "text": window_text})
        win_idx += 1
        pos += step

    return windows


# ── Deduplication ──────────────────────────────────────────────────────


def _deduplicate_scenes(scenes: list[Scene]) -> list[Scene]:
    """Remove near-duplicate scenes that arise from overlapping windows.

    Two scenes are considered duplicates if their combined text content
    has Jaccard similarity >= 0.7.
    """
    if len(scenes) <= 1:
        return scenes

    result = [scenes[0]]
    for scene in scenes[1:]:
        if _jaccard(_scene_text(result[-1]), _scene_text(scene)) < 0.7:
            result.append(scene)
    return result


def _scene_text(scene: Scene) -> str:
    """Concatenate all text content of a scene for similarity comparison."""
    parts = [scene.setting]
    for elem in scene.elements:
        parts.append(elem.content)
    return " ".join(parts)


def _jaccard(a: str, b: str) -> float:
    """Jaccard similarity between two strings based on word sets."""
    words_a = set(a.split())
    words_b = set(b.split())
    if not words_a or not words_b:
        return 0.0
    return len(words_a & words_b) / len(words_a | words_b)
