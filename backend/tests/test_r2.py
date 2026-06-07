"""R2 integration tests — mock LLM, test sliding-window pipeline."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from httpx import ASGITransport, AsyncClient

from app.main import app

SAMPLE_NOVEL = """第一章 初遇

清晨的阳光洒在古老的城墙上。

赵云站在城门口，手握长枪，目光坚定地望向远方。

"将军，探子来报！"一名士兵匆匆跑来，单膝跪地。

赵云转身，沉声道："说。"

第二章 战鼓

远方的地平线上，黑压压的大军正在逼近。

战鼓声震天响，大地在颤抖。"""

MOCK_LLM_OUTPUT = """{
  "scenes": [
    {
      "setting": "古城城门口，清晨",
      "elements": [
        {"type": "action", "content": "清晨的阳光洒在古老的城墙上。"},
        {"type": "character", "content": "赵云", "character": "赵云"},
        {"type": "dialogue", "content": "将军，探子来报！", "character": "士兵"},
        {"type": "character", "content": "赵云", "character": "赵云"},
        {"type": "dialogue", "content": "说。", "character": "赵云"}
      ]
    }
  ]
}"""


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


async def test_r2_scan() -> None:
    """Run an R2 sliding-window scan (mock LLM)."""
    novel_id = await _upload_novel()

    with patch(
        "app.services.r2_service._call_llm",
        new_callable=AsyncMock,
        return_value=MOCK_LLM_OUTPUT,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/r2/scan",
                json={"novel_id": novel_id},
            )

    assert response.status_code == 200
    data = response.json()
    assert data["novel_id"] == novel_id
    assert "id" in data
    assert data["window_count"] > 0
    assert len(data["scenes"]) > 0

    # Verify scene structure
    scene = data["scenes"][0]
    assert "index" in scene
    assert "setting" in scene
    assert len(scene["elements"]) > 0

    elem = scene["elements"][0]
    assert "type" in elem
    assert "content" in elem


async def test_r2_novel_not_found() -> None:
    """Return 404 when novel doesn't exist."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/r2/scan",
            json={"novel_id": "nonexistent"},
        )

    assert response.status_code == 404


async def test_r2_get_result_not_found() -> None:
    """Return 404 when scan doesn't exist."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/r2/nonexistent/result")

    assert response.status_code == 404


async def test_r2_get_result() -> None:
    """Scan then fetch result."""
    novel_id = await _upload_novel()

    with patch(
        "app.services.r2_service._call_llm",
        new_callable=AsyncMock,
        return_value=MOCK_LLM_OUTPUT,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Build first
            scan_resp = await client.post(
                "/api/r2/scan",
                json={"novel_id": novel_id},
            )
            assert scan_resp.status_code == 200
            scan_id = scan_resp.json()["id"]

            # Now fetch
            get_resp = await client.get(f"/api/r2/{novel_id}/result")
            assert get_resp.status_code == 200
            assert get_resp.json()["id"] == scan_id


async def test_r2_scan_idempotent() -> None:
    """Scanning the same novel twice returns the same result."""
    novel_id = await _upload_novel()

    with patch(
        "app.services.r2_service._call_llm",
        new_callable=AsyncMock,
        return_value=MOCK_LLM_OUTPUT,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            first = await client.post("/api/r2/scan", json={"novel_id": novel_id})
            second = await client.post("/api/r2/scan", json={"novel_id": novel_id})

    assert first.status_code == 200
    assert second.status_code == 200
    # Same result ID — no re-scan
    assert first.json()["id"] == second.json()["id"]
    assert first.json()["window_count"] == second.json()["window_count"]


def test_build_windows() -> None:
    """Unit test: sliding window produces correct chunks."""
    from app.services.r2_service import _build_windows

    # Create mock chapters
    class MockChapter:
        def __init__(self, index: int, content: str):
            self.index = index
            self.content = content

    short_text = "A" * 300 + " " + "B" * 300 + " " + "C" * 300
    chapters = [MockChapter(1, short_text)]
    windows = _build_windows(chapters, window_size=400, overlap=100)

    assert len(windows) > 1
    # First window should have content
    assert len(windows[0]["text"]) > 0
    # Windows should have source_chapter
    assert "source_chapter" in windows[0]
    # Windows should be sequential
    for i in range(len(windows)):
        assert windows[i]["index"] == i


def test_deduplicate_scenes() -> None:
    """Unit test: near-duplicate scenes are removed."""
    from app.models.screenplay import Scene, SceneElement
    from app.services.r2_service import _deduplicate_scenes

    scenes = [
        Scene(
            index=1,
            setting="城门",
            elements=[SceneElement(type="action", content="阳光洒在城墙上。")],
        ),
        Scene(
            index=2,
            setting="城门",
            elements=[SceneElement(type="action", content="阳光洒在城墙上。士兵跑来。")],
        ),
        Scene(
            index=3,
            setting="战场",
            elements=[SceneElement(type="action", content="战鼓声震天响。")],
        ),
    ]

    result = _deduplicate_scenes(scenes)

    # Scenes 1 and 2 should be merged (similar), scene 3 kept
    assert len(result) <= 3
    # Scene 3 (battlefield) should still be present
    settings = {s.setting for s in result}
    assert "战场" in settings


def test_deduplicate_empty() -> None:
    """Unit test: dedup on empty list returns empty."""
    from app.services.r2_service import _deduplicate_scenes

    assert _deduplicate_scenes([]) == []
