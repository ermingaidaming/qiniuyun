from __future__ import annotations

from httpx import ASGITransport, AsyncClient

from app.main import app


async def test_health_check() -> None:
    """Health endpoint returns ok status."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "novel-to-screenplay"
