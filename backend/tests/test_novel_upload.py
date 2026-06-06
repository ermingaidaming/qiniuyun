from __future__ import annotations

from httpx import ASGITransport, AsyncClient

from app.main import app


async def test_upload_novel_success() -> None:
    """Upload a valid TXT file and get parsed chapters back."""
    content = "第一章 初遇\n\n这是一段测试文本。\n\n第二章 重逢\n\n这是另一段测试文本。"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/novels/upload",
            files={"file": ("test.txt", content.encode("utf-8"), "text/plain")},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "test.txt"
    assert len(data["chapters"]) >= 1
    assert data["chapters"][0]["index"] == 1
    assert data["chapters"][0]["word_count"] > 0


async def test_upload_rejects_non_txt() -> None:
    """Reject non-TXT files."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/novels/upload",
            files={"file": ("test.pdf", b"not a pdf", "application/pdf")},
        )

    assert response.status_code == 400


async def test_get_novel_not_found() -> None:
    """Return 404 for unknown novel IDs."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/novels/nonexistent-id")

    assert response.status_code == 404
