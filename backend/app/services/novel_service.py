from __future__ import annotations

import re
from pathlib import Path

from app.models.novel import Chapter, Novel

# In-memory storage (replace with database in future PR)
_novels: dict[str, Novel] = {}

# Chapter title patterns: "第X章", "Chapter X", "第X节", blank-line separated blocks
_CHAPTER_PATTERNS = [
    re.compile(r"^第[零一二三四五六七八九十百千万\d]+[章节回].*", re.MULTILINE),
    re.compile(r"^Chapter\s+\d+.*", re.MULTILINE | re.IGNORECASE),
]

_MIN_CHAPTER_LENGTH = 50  # characters


def _parse_title_from_content(content: str, filename: str) -> str:
    """Extract a title from the first non-empty line, fall back to filename."""
    for line in content.splitlines():
        stripped = line.strip()
        if stripped and len(stripped) > 1:
            return stripped[:100]
    return Path(filename).stem


def _split_chapters(text: str) -> list[tuple[str, str]]:
    """Split text into chapters by detecting chapter headings.

    Returns list of (title, content) tuples.
    """
    # Try to find chapter boundaries via regex
    for pattern in _CHAPTER_PATTERNS:
        matches = list(pattern.finditer(text))
        if len(matches) >= 1:
            chapters: list[tuple[str, str]] = []
            for i, match in enumerate(matches):
                start = match.start()
                end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
                title = match.group().strip()
                content = text[start:end].strip()
                if len(content) >= _MIN_CHAPTER_LENGTH:
                    chapters.append((title, content))
            if chapters:
                return chapters

    # Fallback: split by double-newline blocks, group into pseudo-chapters
    blocks = [b.strip() for b in text.split("\n\n") if b.strip()]
    if not blocks:
        return [("全文", text.strip())]

    # Group blocks into chapters of ~2000 chars each
    chapters = []
    buffer = ""
    buffer_title = blocks[0].split("\n")[0][:50] if blocks else "全文"
    chapter_idx = 0

    for block in blocks:
        if len(buffer) + len(block) > 2000 and buffer:
            chapters.append((f"第{chapter_idx + 1}章", buffer.strip()))
            buffer = block
            chapter_idx += 1
        else:
            buffer = f"{buffer}\n\n{block}" if buffer else block

    if buffer.strip():
        chapters.append((f"第{chapter_idx + 1}章" if chapter_idx > 0 else buffer_title, buffer.strip()))

    return chapters


async def parse_novel(filename: str, content: str) -> Novel:
    """Parse an uploaded novel TXT file and create a Novel with chapters."""
    raw_chapters = _split_chapters(content)
    title = _parse_title_from_content(content, filename)

    chapters = [
        Chapter(
            index=i + 1,
            title=chap_title,
            content=chap_content,
            word_count=len(chap_content),
        )
        for i, (chap_title, chap_content) in enumerate(raw_chapters)
    ]

    novel = Novel(title=title, filename=filename, chapters=chapters)
    _novels[novel.id] = novel
    return novel


async def get_novel(novel_id: str) -> Novel | None:
    """Get a novel by ID."""
    return _novels.get(novel_id)
