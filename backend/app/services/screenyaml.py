"""ScreenYAML serialization — Screenplay Pydantic model ↔ ScreenYAML string."""

from __future__ import annotations

from datetime import UTC, datetime

import yaml

from app.models.screenplay import Scene, SceneElement, Screenplay


def _element_to_yaml_dict(elem: SceneElement) -> dict:
    """Convert a SceneElement to its ScreenYAML dict form, keyed by element type."""
    if elem.type == "action":
        return {"type": "action", "content": elem.content}
    elif elem.type == "character":
        return {"type": "character", "name": elem.content}
    elif elem.type == "dialogue":
        return {"type": "dialogue", "character": elem.character or "", "text": elem.content}
    elif elem.type == "parenthetical":
        return {"type": "parenthetical", "character": elem.character or "", "text": elem.content}
    else:
        return {"type": elem.type, "content": elem.content}


def _scene_to_yaml_dict(scene: Scene) -> dict:
    """Convert a Scene to its ScreenYAML dict form."""
    return {
        "scene_id": scene.index,
        "location": scene.location,
        "time": scene.time_of_day,
        "setting": scene.setting,
        "source_chapter": scene.source_chapter,
        "characters": scene.characters,
        "elements": [_element_to_yaml_dict(e) for e in scene.elements],
    }


def screenyaml_dumps(screenplay: Screenplay) -> str:
    """Serialize a Screenplay model to a ScreenYAML string."""
    data = {
        "meta": {
            "title": screenplay.title,
            "source_novel": screenplay.source_novel,
            "novel_author": screenplay.novel_author,
            "total_chapters": screenplay.total_chapters,
            "generated_by": screenplay.generated_by,
            "screenplay_version": "2026-01",
            "created_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        "scenes": [_scene_to_yaml_dict(s) for s in screenplay.scenes],
    }

    # Custom representer for multi-line strings: use | literal block scalar
    class _LiteralStr(str):
        pass

    def _literal_representer(dumper, data):
        if "\n" in data:
            return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
        return dumper.represent_scalar("tag:yaml.org,2002:str", data)

    yaml.add_representer(_LiteralStr, _literal_representer)

    # Wrap multi-line content so YAML uses | block style
    def _wrap_literal(obj):
        if isinstance(obj, dict):
            return {k: _wrap_literal(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_wrap_literal(v) for v in obj]
        if isinstance(obj, str) and len(obj) > 80:
            return _LiteralStr(obj)
        if isinstance(obj, str) and "\n" in obj:
            return _LiteralStr(obj)
        return obj

    wrapped = _wrap_literal(data)

    return yaml.dump(
        wrapped,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
        width=120,
    )
