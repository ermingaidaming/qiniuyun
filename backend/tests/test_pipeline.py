"""Tests for pipeline orchestration — CPC → R2 → HAR → ScreenYAML chain."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from httpx import ASGITransport, AsyncClient

from app.main import app

SAMPLE_NOVEL = """第一章 相遇

咖啡馆里坐满了人。

李明说："今天的咖啡特别香。"

小红轻轻点头，微笑着回答道："是啊，我也喜欢这里。" """

MOCK_CPC_EVENTS = [
    {
        "description": "李明在咖啡馆喝咖啡",
        "characters": ["李明"],
        "location": "咖啡馆",
        "time": "下午",
    },
    {
        "description": "李明与小红交谈",
        "characters": ["李明", "小红"],
        "location": "咖啡馆",
        "time": "下午",
    },
]

MOCK_CPC_RELATIONS = [
    {
        "source_event_id": "e1",
        "target_event_id": "e2",
        "relation_type": "before",
        "confidence": 0.9,
    },
]

MOCK_SCENE = [
    {
        "setting": "咖啡馆，下午",
        "location": "咖啡馆",
        "time_of_day": "下午",
        "characters": ["李明", "小红"],
        "elements": [
            {"type": "action", "content": "咖啡馆里坐满了人。"},
            {"type": "character", "content": "李明"},
            {"type": "dialogue", "content": "今天的咖啡特别香。", "character": "李明"},
        ],
    }
]

MOCK_R2_LLM = '[{"setting":"咖啡馆","location":"咖啡馆","time_of_day":"下午","characters":["李明","小红"],"elements":[{"type":"action","content":"咖啡馆很热闹。"},{"type":"character","content":"李明"},{"type":"dialogue","content":"今天的咖啡特别香。","character":"李明"}]}]'

MOCK_HAR_EMPTY = '{"findings":[]}'


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


async def test_pipeline_full_run() -> None:
    """Full pipeline executes all four steps and returns ScreenYAML."""
    novel_id = await _upload_novel()

    with (
        patch(
            "app.services.cpc_service.extract_events_from_chapter",
            new_callable=AsyncMock,
            return_value=MOCK_CPC_EVENTS,
        ),
        patch(
            "app.services.cpc_service.identify_event_relations",
            new_callable=AsyncMock,
            return_value=MOCK_CPC_RELATIONS,
        ),
        patch(
            "app.services.screenplay_service.convert_chapter_to_scene",
            new_callable=AsyncMock,
            return_value=MOCK_SCENE,
        ),
        patch(
            "app.services.r2_service._call_llm",
            new_callable=AsyncMock,
            return_value=MOCK_R2_LLM,
        ),
        patch(
            "app.services.har_service._call_llm",
            new_callable=AsyncMock,
            return_value=MOCK_HAR_EMPTY,
        ),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/pipeline/run", json={"novel_id": novel_id})

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert data["novel_id"] == novel_id
    assert data["screenyaml"] is not None
    assert data["screenplay_id"] is not None

    # Verify step order and status
    step_names = [s["name"] for s in data["steps"]]
    assert step_names == ["cpc", "r2", "har", "screenyaml"]
    for step in data["steps"]:
        assert step["status"] == "completed"


async def test_pipeline_novel_not_found() -> None:
    """Pipeline returns 404 when novel_id does not exist."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/pipeline/run", json={"novel_id": "nonexistent"})
    assert resp.status_code == 404


async def test_pipeline_partial_cpc_fails() -> None:
    """When CPC fails, pipeline reports partial with cpc=failed."""
    novel_id = await _upload_novel()

    with patch(
        "app.services.cpc_service.build_causal_graph",
        new_callable=AsyncMock,
        side_effect=RuntimeError("LLM timeout"),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/pipeline/run", json={"novel_id": novel_id})

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "partial"
    assert data["screenyaml"] is None
    steps = {s["name"]: s for s in data["steps"]}
    assert steps["cpc"]["status"] == "failed"
    assert "LLM timeout" in steps["cpc"]["error"]


async def test_pipeline_partial_r2_fails() -> None:
    """When R2 fails after CPC succeeded, cpc=completed, r2=failed."""
    novel_id = await _upload_novel()

    with (
        patch(
            "app.services.cpc_service.extract_events_from_chapter",
            new_callable=AsyncMock,
            return_value=MOCK_CPC_EVENTS,
        ),
        patch(
            "app.services.cpc_service.identify_event_relations",
            new_callable=AsyncMock,
            return_value=MOCK_CPC_RELATIONS,
        ),
        patch(
            "app.services.r2_service.scan_novel",
            new_callable=AsyncMock,
            side_effect=RuntimeError("R2 API error"),
        ),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/pipeline/run", json={"novel_id": novel_id})

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "partial"
    steps = {s["name"]: s for s in data["steps"]}
    assert steps["cpc"]["status"] == "completed"
    assert steps["r2"]["status"] == "failed"
    assert "R2 API error" in steps["r2"]["error"]


async def test_pipeline_partial_har_fails() -> None:
    """When HAR fails after CPC+R2, first two complete, har=failed."""
    novel_id = await _upload_novel()

    with (
        patch(
            "app.services.cpc_service.extract_events_from_chapter",
            new_callable=AsyncMock,
            return_value=MOCK_CPC_EVENTS,
        ),
        patch(
            "app.services.cpc_service.identify_event_relations",
            new_callable=AsyncMock,
            return_value=MOCK_CPC_RELATIONS,
        ),
        patch(
            "app.services.r2_service._call_llm",
            new_callable=AsyncMock,
            return_value=MOCK_R2_LLM,
        ),
        patch(
            "app.services.screenplay_service.convert_chapter_to_scene",
            new_callable=AsyncMock,
            return_value=MOCK_SCENE,
        ),
        patch(
            "app.services.har_service.refine",
            new_callable=AsyncMock,
            side_effect=RuntimeError("HAR detect failed"),
        ),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/pipeline/run", json={"novel_id": novel_id})

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "partial"
    steps = {s["name"]: s for s in data["steps"]}
    assert steps["cpc"]["status"] == "completed"
    assert steps["r2"]["status"] == "completed"
    assert steps["har"]["status"] == "failed"


async def test_pipeline_idempotent() -> None:
    """Second pipeline run returns completed — all steps skip redo."""
    novel_id = await _upload_novel()

    with (
        patch(
            "app.services.cpc_service.extract_events_from_chapter",
            new_callable=AsyncMock,
            return_value=MOCK_CPC_EVENTS,
        ),
        patch(
            "app.services.cpc_service.identify_event_relations",
            new_callable=AsyncMock,
            return_value=MOCK_CPC_RELATIONS,
        ),
        patch(
            "app.services.screenplay_service.convert_chapter_to_scene",
            new_callable=AsyncMock,
            return_value=MOCK_SCENE,
        ),
        patch(
            "app.services.r2_service._call_llm",
            new_callable=AsyncMock,
            return_value=MOCK_R2_LLM,
        ),
        patch(
            "app.services.har_service._call_llm",
            new_callable=AsyncMock,
            return_value=MOCK_HAR_EMPTY,
        ),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp1 = await client.post("/api/pipeline/run", json={"novel_id": novel_id})
            resp2 = await client.post("/api/pipeline/run", json={"novel_id": novel_id})

    assert resp1.status_code == 200
    assert resp2.status_code == 200
    assert resp1.json()["status"] == "completed"
    assert resp2.json()["status"] == "completed"
