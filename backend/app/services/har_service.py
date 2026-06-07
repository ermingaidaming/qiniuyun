"""HAR (Hallucination-Aware Refinement) service.

Pipeline:
  scenes → per-scene source lookup → LLM fact-check → apply corrections → re-verify
"""

from __future__ import annotations

import json
import uuid
from copy import deepcopy
from typing import Any

from app.core.config import settings
from app.db.engine import async_session
from app.db.repository.har import get_report_by_novel as _db_get_report
from app.db.repository.har import save_report as _db_save_report
from app.models.har import HARFinding, HARReport
from app.models.novel import Novel
from app.models.screenplay import Scene
from app.services.llm_service import _call_llm
from app.services.screenplay_service import generate_screenplay, get_screenplay_by_novel

# ── HAR prompts ───────────────────────────────────────────────────────

HAR_SYSTEM_PROMPT = (
    "你是一位专业的剧本事实核查员。"
    "请对比原始小说文本和AI生成的剧本场景，找出所有事实性不一致（\"幻觉\"）。\n"
    "\n"
    "## 幻觉类型\n"
    "\n"
    "- **character**: 角色名错误、角色不存在、角色关系错误\n"
    "- **event**: 事件未发生、事件顺序错误、事件描述与原文不符\n"
    "- **dialogue**: 对话内容与原文不符、说话人错误\n"
    "- **setting**: 地点错误、时间错误、环境描述错误\n"
    "- **detail**: 其他与原文不一致的细节\n"
    "\n"
    "## 严重程度\n"
    "\n"
    "- **critical**: 完全虚构或严重歪曲原文，影响剧情走向\n"
    "- **major**: 重要细节错误，但整体方向正确\n"
    "- **minor**: 小瑕疵，不影响整体理解\n"
    "\n"
    "## 输出格式\n"
    "\n"
    "返回严格的 JSON 对象：\n"
    "```json\n"
    "{\n"
    '  "findings": [\n'
    "    {\n"
    '      "scene_index": 1,\n'
    '      "severity": "major",\n'
    '      "category": "character",\n'
    '      "description": "问题描述",\n'
    '      "hallucinated_text": "剧本中错误的原文",\n'
    '      "suggested_fix": "建议修正后的文本",\n'
    '      "source_evidence": "原文引用证据"\n'
    "    }\n"
    "  ]\n"
    "}\n"
    "```\n"
    "\n"
    "## 规则\n"
    "\n"
    "1. 只报告确凿的事实错误，不要报告风格或措辞偏好\n"
    '2. 如果没有发现任何幻觉，返回 {"findings": []}\n'
    "3. 每个 finding 必须提供 source_evidence（原文引用）\n"
    "4. suggested_fix 必须基于原文，不能凭空创造\n"
    "5. JSON 必须合法，不要输出 Markdown 代码块包裹"
)

HAR_USER_TEMPLATE = """## 原始小说文本（第{chapter_index}章：{chapter_title}）

{source_text}

## AI 生成的剧本场景

场景 {scene_index}：{setting}
地点：{location}  时间：{time}

{elements_text}"""

MAX_VERIFICATION_ROUNDS = 2


# ── Public API ────────────────────────────────────────────────────────


async def refine(novel: Novel) -> HARReport:
    """Run HAR hallucination detection and self-correction on a novel's screenplay."""
    # Idempotent: return existing report
    async with async_session() as session:
        existing = await _db_get_report(session, novel.id)
        if existing is not None:
            return existing

    # Get or generate screenplay
    screenplay = await get_screenplay_by_novel(novel.id)
    if screenplay is None:
        screenplay = await generate_screenplay(novel)

    scenes = screenplay.scenes
    if not scenes:
        report = HARReport(
            id=str(uuid.uuid4()),
            novel_id=novel.id,
            total_scenes=0,
            total_findings=0,
        )
        async with async_session() as session:
            await _db_save_report(session, report)
        return report

    # Build chapter lookup
    chapter_map = {ch.index: ch for ch in novel.chapters}

    all_findings: list[HARFinding] = []
    corrected_scenes = deepcopy(scenes)

    for round_num in range(1, MAX_VERIFICATION_ROUNDS + 1):
        round_findings = await _detect_hallucinations(corrected_scenes, chapter_map, round_num)
        if not round_findings:
            break
        all_findings.extend(round_findings)
        _apply_corrections(corrected_scenes, round_findings)

    # ── Persist ────────────────────────────────────────────────────
    report = HARReport(
        id=str(uuid.uuid4()),
        novel_id=novel.id,
        total_scenes=len(scenes),
        total_findings=len(all_findings),
        findings=all_findings,
        corrected_scenes=corrected_scenes,
        verification_rounds=MAX_VERIFICATION_ROUNDS if all_findings else 1,
    )
    async with async_session() as session:
        await _db_save_report(session, report)

    return report


async def get_report(novel_id: str) -> HARReport | None:
    """Get the HAR report for a novel."""
    async with async_session() as session:
        return await _db_get_report(session, novel_id)


# ── Hallucination Detection ───────────────────────────────────────────


async def _detect_hallucinations(
    scenes: list[Scene],
    chapter_map: dict[int, Any],
    round_num: int,
) -> list[HARFinding]:
    """Detect hallucinations by comparing each scene against source text."""
    findings: list[HARFinding] = []

    for scene in scenes:
        chapter = chapter_map.get(scene.source_chapter)
        if chapter is None:
            continue

        # Build scene text for LLM
        elements_text = "\n".join(
            f"[{e.type}] {e.character + ': ' if e.character else ''}{e.content}" for e in scene.elements
        )

        try:
            raw = await _call_llm(
                HAR_SYSTEM_PROMPT,
                HAR_USER_TEMPLATE.format(
                    chapter_index=chapter.index,
                    chapter_title=chapter.title,
                    source_text=chapter.content[: settings.max_chapter_length_chars],
                    scene_index=scene.index,
                    setting=scene.setting,
                    location=scene.location,
                    time=scene.time_of_day,
                    elements_text=elements_text,
                ),
                temperature=0.3,  # low temperature for factual tasks
            )
            parsed = _parse_har_response(raw)
            for f in parsed:
                findings.append(
                    HARFinding(
                        scene_index=int(f.get("scene_index", scene.index)),
                        severity=f.get("severity", "minor"),  # type: ignore[arg-type]
                        category=f.get("category", "detail"),  # type: ignore[arg-type]
                        description=str(f.get("description", "")),
                        hallucinated_text=str(f.get("hallucinated_text", "")),
                        suggested_fix=str(f.get("suggested_fix", "")),
                        source_evidence=str(f.get("source_evidence", "")),
                    )
                )
        except Exception:
            continue

    return findings


# ── Correction Application ────────────────────────────────────────────


def _apply_corrections(scenes: list[Scene], findings: list[HARFinding]) -> None:
    """Apply suggested fixes to scenes in-place by string replacement."""
    scene_map: dict[int, Scene] = {s.index: s for s in scenes}

    for f in findings:
        if not f.hallucinated_text or not f.suggested_fix:
            continue
        scene = scene_map.get(f.scene_index)
        if scene is None:
            continue

        for elem in scene.elements:
            if f.hallucinated_text in elem.content:
                elem.content = elem.content.replace(f.hallucinated_text, f.suggested_fix)
            if elem.character and f.hallucinated_text in elem.character:
                elem.character = elem.character.replace(f.hallucinated_text, f.suggested_fix)


# ── Response Parsing ──────────────────────────────────────────────────


def _parse_har_response(raw: str) -> list[dict[str, Any]]:
    """Parse LLM hallucination detection response."""
    # Try direct parse
    try:
        data = json.loads(raw)
        if isinstance(data, dict) and "findings" in data:
            return data["findings"]
    except json.JSONDecodeError:
        pass

    # Try markdown code block
    import re

    code_block = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    if code_block:
        try:
            data = json.loads(code_block.group(1))
            if isinstance(data, dict) and "findings" in data:
                return data["findings"]
        except json.JSONDecodeError:
            pass

    # Try to find JSON object
    brace_start = raw.find("{")
    brace_end = raw.rfind("}")
    if brace_start != -1 and brace_end != -1:
        try:
            data = json.loads(raw[brace_start : brace_end + 1])
            if isinstance(data, dict) and "findings" in data:
                return data["findings"]
        except json.JSONDecodeError:
            pass

    return []
