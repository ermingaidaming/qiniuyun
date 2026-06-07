from __future__ import annotations

import json
import re
from typing import Any, cast

from httpx import AsyncClient

from app.core.config import settings

# Prompt template for novel-to-screenplay conversion
SYSTEM_PROMPT = """你是一位专业的剧本编剧。请将以下小说文本转化为标准剧本格式。

## 输出要求

你必须返回一个严格的 JSON 对象，格式如下：
```json
{
  "scenes": [
    {
      "location": "地点（如：青云宗练功场、山崖之巅、迎客大厅）",
      "time": "时间（如：清晨、深夜、次日午后、黄昏）",
      "setting": "场景氛围描述（一句话概括场景的环境和气氛）",
      "characters": ["出场角色1", "出场角色2"],
      "elements": [
        {"type": "action", "content": "动作描述或场景说明"},
        {"type": "character", "content": "角色名", "character": "角色名"},
        {"type": "dialogue", "content": "角色说的话", "character": "角色名"},
        {"type": "parenthetical", "content": "括号内的情绪/动作提示", "character": "角色名"}
      ]
    }
  ]
}
```

## 字段说明

- **location**: 场景发生的地点，独立于 setting。如场景在多个地点切换，选主要地点。
- **time**: 场景发生的时间（时刻或时段），独立于 setting。
- **setting**: 场景的整体氛围描述，包含环境细节、天气、人群等。
- **characters**: 本场景中所有说话或有重要动作的角色名列表。

## 元素类型说明

- **action**: 动作描述、场景氛围、环境描写。content 为描述文本。
- **character**: 角色名出场标记。content 和 character 都为角色名。对话前必须先用 character 标记说话人。
- **dialogue**: 角色对话。必须设置 character 字段为说话角色名。
- **parenthetical**: 对话中的情绪提示或动作提示，如"(激动地)"、"(低声)"。必须设置 character 字段。

## 规则

1. 每个场景必须包含 location、time、setting 和至少一个 action 元素。
2. 对话前必须先用 character 元素标记说话人。
3. 对话之间的情绪/动作提示使用 parenthetical 类型。
4. characters 列表必须列出本场景所有说话人和重要角色。
5. JSON 必须合法，不要输出任何 JSON 之外的文本。
6. 不要使用 Markdown 代码块包裹 JSON。
"""

USER_PROMPT_TEMPLATE = """请将以下小说章节片段转化为剧本格式：

## 章节：{chapter_title}

{chapter_content}
"""


async def _call_llm(system_prompt: str, user_prompt: str, *, temperature: float = 0.7, max_tokens: int = 4096) -> str:
    """Generic LLM call. Returns the content of the first choice."""
    async with AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{settings.llm_base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.llm_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.llm_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
        )

    if response.status_code != 200:
        raise RuntimeError(f"LLM API error: {response.status_code} {response.text[:200]}")

    data = response.json()
    return cast(str, data["choices"][0]["message"]["content"])


async def convert_chapter_to_scene(chapter_title: str, chapter_content: str) -> list[dict[str, Any]]:
    """Call LLM to convert a single chapter into screenplay scenes.

    Returns a list of scene dicts parsed from the LLM response.
    """
    if not settings.llm_api_key:
        return _mock_convert(chapter_title, chapter_content)

    raw = await _call_llm(
        SYSTEM_PROMPT,
        USER_PROMPT_TEMPLATE.format(
            chapter_title=chapter_title,
            chapter_content=chapter_content[: settings.max_chapter_length_chars],
        ),
        max_tokens=8192,
    )
    return _parse_llm_json(raw)


def _parse_llm_json(raw: str) -> list[dict[str, Any]]:
    """Parse LLM response into a list of scene dicts. Handles common formatting issues."""
    # Try direct JSON parse first
    try:
        data = json.loads(raw)
        if isinstance(data, dict) and "scenes" in data:
            return cast(list[dict[str, Any]], data["scenes"])
        if isinstance(data, list):
            return cast(list[dict[str, Any]], data)
    except json.JSONDecodeError:
        pass

    # Try to extract JSON from markdown code blocks
    code_block = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    if code_block:
        try:
            data = json.loads(code_block.group(1))
            if isinstance(data, dict) and "scenes" in data:
                return cast(list[dict[str, Any]], data["scenes"])
            if isinstance(data, list):
                return cast(list[dict[str, Any]], data)
        except json.JSONDecodeError:
            pass

    # Try to find JSON object in the text
    brace_start = raw.find("{")
    brace_end = raw.rfind("}")
    if brace_start != -1 and brace_end != -1:
        try:
            data = json.loads(raw[brace_start : brace_end + 1])
            if isinstance(data, dict) and "scenes" in data:
                return cast(list[dict[str, Any]], data["scenes"])
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Failed to parse LLM response as JSON. Raw: {raw[:200]}...")


def _mock_convert(chapter_title: str, chapter_content: str) -> list[dict[str, Any]]:
    """Generate a mock scene when no LLM API key is configured.

    This ensures the pipeline works end-to-end for development and testing.
    """
    lines = [line.strip() for line in chapter_content.splitlines() if line.strip()]
    elements: list[dict[str, Any]] = []

    # Opening action
    elements.append({"type": "action", "content": f"{chapter_title}。场景开始。"})

    current_character: str | None = None
    characters_seen: set[str] = set()

    for _i, line in enumerate(lines[:30]):  # Limit to 30 lines for mock
        if len(line) < 3:
            continue

        # Heuristic: if line has quotes, treat as dialogue
        if "说" in line or "道" in line or "：" in line or "：" in line:
            # Extract character and dialogue
            for sep in ("说：", "说道：", "道：", "：", "："):
                if sep in line:
                    parts = line.split(sep, 1)
                    char_name = parts[0].strip().split()[-1] if parts[0].strip() else "角色"
                    dialogue = parts[1].strip().strip("“”‘’\"'") if len(parts) > 1 else ""
                    if not dialogue:
                        dialogue = line
                    elements.append({"type": "character", "content": char_name, "character": char_name})
                    elements.append({"type": "dialogue", "content": dialogue, "character": char_name})
                    characters_seen.add(char_name)
                    current_character = char_name
                    break
            else:
                # Treat whole line as dialogue from current character
                char_name = current_character or "旁白"
                characters_seen.add(char_name)
                elements.append({"type": "character", "content": char_name, "character": char_name})
                elements.append({"type": "dialogue", "content": line, "character": char_name})
        elif current_character and (line.startswith("(") or line.startswith("（")):
            elements.append({"type": "parenthetical", "content": line, "character": current_character})
        else:
            elements.append({"type": "action", "content": line})

    return [{
        "location": "",
        "time": "",
        "setting": chapter_title,
        "characters": list(characters_seen),
        "elements": elements,
    }]


# ── CPC Event Extraction ─────────────────────────────────────────────

CPC_EVENT_SYSTEM_PROMPT = """你是一位专业的文学分析师。请从小说文本中提取所有关键剧情事件。

## 输出要求

你必须返回一个严格的 JSON 对象：
```json
{
  "events": [
    {
      "description": "事件描述（一句话概括）",
      "characters": ["参与角色1", "参与角色2"],
      "location": "发生地点",
      "time": "发生时间"
    }
  ]
}
```

## 规则

1. 每个事件必须是独立的、推动剧情发展的关键节点。
2. 同一个场景中可能包含多个事件，请逐一提取。
3. 角色名使用中文原名。
4. 如果无法确定地点或时间，使用空字符串 ""。
5. JSON 必须合法，不要输出 Markdown 代码块包裹。
"""

CPC_EVENT_USER_TEMPLATE = """请从以下小说章节中提取关键事件：

## 章节：{chapter_title}

{chapter_content}
"""

CPC_RELATION_SYSTEM_PROMPT = """你是一位专业的文学分析师。请分析以下事件之间的因果关系和时序关系。

## 输出要求

返回一个严格的 JSON 对象：
```json
{
  "relations": [
    {
      "source_event_id": "事件A的id",
      "target_event_id": "事件B的id",
      "relation_type": "causes|before|references",
      "confidence": 0.9
    }
  ]
}
```

## 关系类型说明

- **causes**: A 直接导致 B 发生（因果关系）
- **before**: A 在 B 之前发生（时序关系）
- **references**: A 和 B 提及同一事物或角色（引用关系）

## 规则

1. 只标注明确存在的关系，不要猜测。
2. confidence 取值 0.0-1.0：1.0 = 非常确定，0.5 = 可能有关。
3. JSON 必须合法，不要输出 Markdown 代码块包裹。
"""

CPC_RELATION_USER_TEMPLATE = """请分析以下事件的因果关系：

{events_json}
"""


async def extract_events_from_chapter(chapter_title: str, chapter_content: str) -> list[dict[str, Any]]:
    """Extract key plot events from a chapter via LLM."""
    if not settings.llm_api_key:
        return _mock_extract_events(chapter_title, chapter_content)

    raw = await _call_llm(
        CPC_EVENT_SYSTEM_PROMPT,
        CPC_EVENT_USER_TEMPLATE.format(
            chapter_title=chapter_title,
            chapter_content=chapter_content[: settings.max_chapter_length_chars],
        ),
    )
    parsed = _parse_json_field(raw, "events")
    return parsed


async def identify_event_relations(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Identify causal and temporal relationships between events via LLM."""
    if not settings.llm_api_key:
        return []

    raw = await _call_llm(
        CPC_RELATION_SYSTEM_PROMPT,
        CPC_RELATION_USER_TEMPLATE.format(events_json=json.dumps(events, ensure_ascii=False)),
        max_tokens=8192,
    )
    parsed = _parse_json_field(raw, "relations")
    return parsed


def _parse_json_field(raw: str, field: str) -> list[dict[str, Any]]:
    """Parse LLM response, extracting a named list field. Handles common formatting issues."""
    # Try direct JSON parse
    try:
        data = json.loads(raw)
        if isinstance(data, dict) and field in data:
            return cast(list[dict[str, Any]], data[field])
    except json.JSONDecodeError:
        pass

    # Try markdown code block
    code_block = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    if code_block:
        try:
            data = json.loads(code_block.group(1))
            if isinstance(data, dict) and field in data:
                return cast(list[dict[str, Any]], data[field])
        except json.JSONDecodeError:
            pass

    # Try to find JSON object in text
    brace_start = raw.find("{")
    brace_end = raw.rfind("}")
    if brace_start != -1 and brace_end != -1:
        try:
            data = json.loads(raw[brace_start : brace_end + 1])
            if isinstance(data, dict) and field in data:
                return cast(list[dict[str, Any]], data[field])
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Failed to parse LLM response JSON (field={field}). Raw: {raw[:200]}...")


def _mock_extract_events(chapter_title: str, chapter_content: str) -> list[dict[str, Any]]:
    """Mock event extraction for testing without LLM."""
    events: list[dict[str, Any]] = []
    for line in chapter_content.splitlines():
        line = line.strip()
        if len(line) < 5:
            continue
        # Heuristic: lines with dialogue markers indicate key events
        if any(kw in line for kw in ("说", "道", "来", "去", "走", "看", "见", "笑", "哭")):
            events.append({
                "description": line[:80],
                "characters": [],
                "location": "",
                "time": "",
            })
    if not events:
        events.append({"description": f"{chapter_title} 的主要情节", "characters": [], "location": "", "time": ""})
    return events[:10]  # Limit to 10 mock events per chapter
