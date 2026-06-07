from __future__ import annotations

from httpx import ASGITransport, AsyncClient

from app.main import app

SAMPLE_NOVEL = """第一章 相遇

咖啡馆里坐满了人。

李明说："今天的咖啡特别香。"

小红轻轻点头，（微笑着）回答道："是啊，我也喜欢这里。"小雨抬头看了看窗外。

第二章 离别

天色渐暗，街道行人稀少。他们默默走在石板路上。"""


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


async def test_generate_screenplay_mock() -> None:
    """Generate a screenplay using the mock LLM (no API key needed)."""
    novel_id = await _upload_novel()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/screenplay/generate",
            json={"novel_id": novel_id},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["novel_id"] == novel_id
    assert len(data["scenes"]) >= 1
    assert data["scenes"][0]["index"] == 1
    assert "elements" in data["scenes"][0]

    # Verify at least one scene element has valid structure
    elements = data["scenes"][0]["elements"]
    assert len(elements) > 0
    assert elements[0]["type"] in ("action", "character", "dialogue", "parenthetical")
    assert "content" in elements[0]


async def test_generate_screenplay_novel_not_found() -> None:
    """Return 404 when novel doesn't exist."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/screenplay/generate",
            json={"novel_id": "nonexistent"},
        )

    assert response.status_code == 404


async def test_get_screenplay_not_found() -> None:
    """Return 404 when screenplay doesn't exist."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/screenplay/nonexistent")

    assert response.status_code == 404


async def test_generate_idempotent() -> None:
    """Second generate request returns the same screenplay."""
    novel_id = await _upload_novel()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r1 = await client.post("/api/screenplay/generate", json={"novel_id": novel_id})
        r2 = await client.post("/api/screenplay/generate", json={"novel_id": novel_id})

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["id"] == r2.json()["id"]  # Same screenplay returned
