"""HAR integration tests — mock LLM, test hallucination detection pipeline."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from httpx import ASGITransport, AsyncClient

from app.main import app

SAMPLE_NOVEL = """第一章 初遇

清晨的阳光洒在古老的城墙上。

守将站在城门口，手握长枪，目光坚定地望向远方。

"将军，探子来报！"一名士兵匆匆跑来，单膝跪地。

守将转身，沉声道："说。"

第二章 战鼓

远方的地平线上，黑压压的大军正在逼近。

战鼓声震天响，大地在颤抖。"""

MOCK_SCENE = [
    {
        "setting": "古城城门口，清晨",
        "elements": [
            {"type": "action", "content": "清晨的阳光洒在古老的城墙上。"},
            {"type": "character", "content": "赵云", "character": "赵云"},
            {"type": "dialogue", "content": "将军，探子来报！", "character": "士兵"},
        ],
    }
]

MOCK_HAR_FINDINGS = """{
  "findings": [
    {
      "scene_index": 1,
      "severity": "major",
      "category": "character",
      "description": "角色'赵云'不存在于原文中，原文是'守将'",
      "hallucinated_text": "赵云",
      "suggested_fix": "守将",
      "source_evidence": "原文：守将站在城门口，手握长枪"
    }
  ]
}"""

MOCK_HAR_EMPTY = '{"findings": []}'


async def _upload_novel() -> str:
    """Helper: upload a sample novel and return its ID."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/novels/upload",
            files={"file": ("sample.txt", SAMPLE_NOVEL.encode("utf-8"), "text/plain")},
        )
    assert response.status_code == 200
    return response.json()["id"]


async def test_har_refine() -> None:
    """Run HAR hallucination detection (mock LLM)."""
    novel_id = await _upload_novel()

    with (
        patch(
            "app.services.screenplay_service.convert_chapter_to_scene",
            new_callable=AsyncMock,
            return_value=MOCK_SCENE,
        ),
        patch(
            "app.services.har_service._call_llm",
            new_callable=AsyncMock,
            return_value=MOCK_HAR_FINDINGS,
        ),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/har/refine",
                json={"novel_id": novel_id},
            )

    assert response.status_code == 200
    data = response.json()
    assert data["novel_id"] == novel_id
    assert "id" in data
    assert data["total_scenes"] > 0
    assert data["total_findings"] > 0
    assert len(data["findings"]) > 0

    finding = data["findings"][0]
    assert "scene_index" in finding
    assert finding["severity"] in ("critical", "major", "minor")
    assert finding["category"] in ("character", "event", "dialogue", "setting", "detail")

    # Corrected scenes should exist
    assert len(data["corrected_scenes"]) > 0


async def test_har_novel_not_found() -> None:
    """Return 404 when novel doesn't exist."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/har/refine",
            json={"novel_id": "nonexistent"},
        )

    assert response.status_code == 404


async def test_har_get_report_not_found() -> None:
    """Return 404 when report doesn't exist."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/har/nonexistent/report")

    assert response.status_code == 404


async def test_har_get_report() -> None:
    """Refine then fetch report."""
    novel_id = await _upload_novel()

    with (
        patch(
            "app.services.screenplay_service.convert_chapter_to_scene",
            new_callable=AsyncMock,
            return_value=MOCK_SCENE,
        ),
        patch(
            "app.services.har_service._call_llm",
            new_callable=AsyncMock,
            return_value=MOCK_HAR_FINDINGS,
        ),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            refine_resp = await client.post("/api/har/refine", json={"novel_id": novel_id})
            assert refine_resp.status_code == 200
            report_id = refine_resp.json()["id"]

            get_resp = await client.get(f"/api/har/{novel_id}/report")
            assert get_resp.status_code == 200
            assert get_resp.json()["id"] == report_id


async def test_har_refine_idempotent() -> None:
    """Refining the same novel twice returns the same report."""
    novel_id = await _upload_novel()

    with (
        patch(
            "app.services.screenplay_service.convert_chapter_to_scene",
            new_callable=AsyncMock,
            return_value=MOCK_SCENE,
        ),
        patch(
            "app.services.har_service._call_llm",
            new_callable=AsyncMock,
            return_value=MOCK_HAR_FINDINGS,
        ),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            first = await client.post("/api/har/refine", json={"novel_id": novel_id})
            second = await client.post("/api/har/refine", json={"novel_id": novel_id})

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]


async def test_har_no_hallucinations() -> None:
    """Empty findings — LLM reports no hallucinations."""
    novel_id = await _upload_novel()

    with (
        patch(
            "app.services.screenplay_service.convert_chapter_to_scene",
            new_callable=AsyncMock,
            return_value=MOCK_SCENE,
        ),
        patch(
            "app.services.har_service._call_llm",
            new_callable=AsyncMock,
            return_value=MOCK_HAR_EMPTY,
        ),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/har/refine",
                json={"novel_id": novel_id},
            )

    assert response.status_code == 200
    data = response.json()
    assert data["total_findings"] == 0
    assert len(data["findings"]) == 0
    # Corrected scenes should equal original
    assert len(data["corrected_scenes"]) > 0


def test_apply_corrections() -> None:
    """Unit test: text replacement in scenes."""
    from app.models.har import HARFinding
    from app.models.screenplay import Scene, SceneElement
    from app.services.har_service import _apply_corrections

    scenes = [
        Scene(
            index=1,
            setting="城门",
            elements=[
                SceneElement(type="action", content="赵云站在城门口。"),
                SceneElement(type="dialogue", content="来吧！", character="赵云"),
            ],
        )
    ]

    findings = [
        HARFinding(
            scene_index=1,
            severity="major",
            category="character",
            description="角色名错误",
            hallucinated_text="赵云",
            suggested_fix="守将",
            source_evidence="原文：守将站在城门口",
        )
    ]

    _apply_corrections(scenes, findings)

    # "赵云" should be replaced with "守将" in all elements
    assert "赵云" not in scenes[0].elements[0].content
    assert "守将" in scenes[0].elements[0].content
    assert "守将" in scenes[0].elements[1].character
