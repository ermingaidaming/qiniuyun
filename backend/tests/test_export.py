from __future__ import annotations

from httpx import ASGITransport, AsyncClient

from app.main import app

SAMPLE_NOVEL = """第一章 测试

这是一段动作描述。

张三说："你好，世界。"

李四回答道："你好。"
"""


async def _upload_and_generate() -> str:
    """Helper: upload a novel and generate screenplay, return screenplay ID."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Upload
        resp = await client.post(
            "/api/novels/upload",
            files={"file": ("test.txt", SAMPLE_NOVEL.encode("utf-8"), "text/plain")},
        )
        novel_id = resp.json()["id"]

        # Generate
        resp = await client.post("/api/screenplay/generate", json={"novel_id": novel_id})
        return resp.json()["id"]


async def test_export_txt() -> None:
    """Export screenplay as TXT."""
    sp_id = await _upload_and_generate()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/export/{sp_id}?format=txt")

    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    content = response.content.decode("utf-8")
    assert "剧本" in content
    assert len(content) > 50


async def test_export_docx() -> None:
    """Export screenplay as DOCX."""
    sp_id = await _upload_and_generate()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/export/{sp_id}?format=docx")

    assert response.status_code == 200
    assert "wordprocessingml" in response.headers["content-type"]
    assert len(response.content) > 100  # DOCX is a ZIP with XML


async def test_export_yaml() -> None:
    """Export screenplay as ScreenYAML."""
    sp_id = await _upload_and_generate()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/export/{sp_id}?format=yaml")

    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "meta:" in content
    assert "scenes:" in content
    assert "scene_id" in content
    assert "elements:" in content
    # Verify it's valid YAML
    import yaml
    data = yaml.safe_load(content)
    assert "meta" in data
    assert "scenes" in data
    assert len(data["scenes"]) > 0
    assert "elements" in data["scenes"][0]


async def test_export_invalid_format() -> None:
    """Reject invalid export format."""
    sp_id = await _upload_and_generate()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/export/{sp_id}?format=pdf")

    assert response.status_code == 422  # Validation error


async def test_export_not_found() -> None:
    """Return 404 for unknown screenplay."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/export/nonexistent?format=txt")

    assert response.status_code == 404
