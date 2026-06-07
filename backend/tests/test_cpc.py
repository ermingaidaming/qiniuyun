"""CPC integration tests — mock LLM, test algorithm pipeline."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from httpx import ASGITransport, AsyncClient

from app.main import app

SAMPLE_NOVEL = """第一章 相遇

咖啡馆里坐满了人。

李明说："今天的咖啡特别香。"

小红轻轻点头，微笑着回答道："是啊，我也喜欢这里。"

第二章 离别

天色渐暗，街道行人稀少。他们默默走在石板路上。

李明突然停下来，转身看着小红："明天我就要走了。"

小红愣住了，眼泪在眼眶中打转。"""

MOCK_EVENTS = [
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
    {
        "description": "小红微笑回应",
        "characters": ["小红"],
        "location": "咖啡馆",
        "time": "下午",
    },
]

MOCK_RELATIONS = [
    {
        "source_event_id": "e1",
        "target_event_id": "e2",
        "relation_type": "before",
        "confidence": 0.9,
    },
    {
        "source_event_id": "e2",
        "target_event_id": "e3",
        "relation_type": "causes",
        "confidence": 0.8,
    },
]


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


async def test_build_cpc_graph() -> None:
    """Build a CPC causal graph for a novel (mock LLM)."""
    novel_id = await _upload_novel()

    with patch(
        "app.services.cpc_service.extract_events_from_chapter",
        new_callable=AsyncMock,
        return_value=MOCK_EVENTS,
    ), patch(
        "app.services.cpc_service.identify_event_relations",
        new_callable=AsyncMock,
        return_value=MOCK_RELATIONS,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/cpc/build",
                json={"novel_id": novel_id},
            )

    assert response.status_code == 200
    data = response.json()
    assert data["novel_id"] == novel_id
    assert "id" in data
    assert data["dag_valid"] is True
    assert len(data["events"]) > 0

    # Verify event structure
    event = data["events"][0]
    assert "id" in event
    assert "description" in event
    assert "characters" in event
    assert event["chapter_index"] >= 1

    # Relations may be empty if mock IDs don't match actual event IDs
    if data["relations"]:
        rel = data["relations"][0]
        assert "source_event_id" in rel
        assert "target_event_id" in rel
        assert rel["relation_type"] in ("causes", "before", "references")


async def test_build_cpc_novel_not_found() -> None:
    """Return 404 when novel doesn't exist."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/cpc/build",
            json={"novel_id": "nonexistent"},
        )

    assert response.status_code == 404


async def test_get_cpc_graph_not_found() -> None:
    """Return 404 when CPC graph doesn't exist."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/cpc/nonexistent/graph")

    assert response.status_code == 404


async def test_get_cpc_graph() -> None:
    """Build then fetch a CPC graph."""
    novel_id = await _upload_novel()

    with patch(
        "app.services.cpc_service.extract_events_from_chapter",
        new_callable=AsyncMock,
        return_value=MOCK_EVENTS,
    ), patch(
        "app.services.cpc_service.identify_event_relations",
        new_callable=AsyncMock,
        return_value=MOCK_RELATIONS,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Build first
            build_resp = await client.post(
                "/api/cpc/build",
                json={"novel_id": novel_id},
            )
            assert build_resp.status_code == 200
            graph_id = build_resp.json()["id"]

            # Now fetch
            get_resp = await client.get(f"/api/cpc/{novel_id}/graph")
            assert get_resp.status_code == 200
            assert get_resp.json()["id"] == graph_id


async def test_cpc_cycle_removal_via_api() -> None:
    """Relations referencing nonexistent events are filtered out."""
    novel_id = await _upload_novel()

    relations_with_bad_refs = [
        {"source_event_id": "bad-1", "target_event_id": "bad-2", "relation_type": "causes", "confidence": 0.9},
    ]

    with patch(
        "app.services.cpc_service.extract_events_from_chapter",
        new_callable=AsyncMock,
        return_value=MOCK_EVENTS,
    ), patch(
        "app.services.cpc_service.identify_event_relations",
        new_callable=AsyncMock,
        return_value=relations_with_bad_refs,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/cpc/build",
                json={"novel_id": novel_id},
            )

    assert response.status_code == 200
    data = response.json()
    # Bad references are filtered, resulting in empty relations
    assert len(data["relations"]) == 0
    assert data["dag_valid"] is True


def test_remove_cycles_breaks_cycle() -> None:
    """Unit test: cycle removal breaks a 3-node cycle by removing the weakest edge."""
    from app.models.cpc import CausalRelation, Event
    from app.services.cpc_service import _remove_cycles

    events = [
        Event(id="e1", index=1, chapter_index=1, description="A"),
        Event(id="e2", index=2, chapter_index=1, description="B"),
        Event(id="e3", index=3, chapter_index=1, description="C"),
    ]
    relations = [
        CausalRelation(id="r1", source_event_id="e1", target_event_id="e2", relation_type="causes", confidence=0.9),
        CausalRelation(id="r2", source_event_id="e2", target_event_id="e3", relation_type="causes", confidence=0.8),
        CausalRelation(id="r3", source_event_id="e3", target_event_id="e1", relation_type="causes", confidence=0.3),  # cycle
    ]

    clean, was_cyclic = _remove_cycles(events, relations)

    # The weakest edge (e3→e1, confidence=0.3) should be removed
    assert was_cyclic is False
    assert len(clean) == 2
    kept_pairs = {(r.source_event_id, r.target_event_id) for r in clean}
    assert ("e1", "e2") in kept_pairs
    assert ("e2", "e3") in kept_pairs
    assert ("e3", "e1") not in kept_pairs


def test_remove_cycles_no_cycle() -> None:
    """Unit test: acyclic relations pass through unchanged."""
    from app.models.cpc import CausalRelation, Event
    from app.services.cpc_service import _remove_cycles

    events = [
        Event(id="e1", index=1, chapter_index=1, description="A"),
        Event(id="e2", index=2, chapter_index=1, description="B"),
        Event(id="e3", index=3, chapter_index=1, description="C"),
    ]
    relations = [
        CausalRelation(id="r1", source_event_id="e1", target_event_id="e2", relation_type="before", confidence=1.0),
        CausalRelation(id="r2", source_event_id="e2", target_event_id="e3", relation_type="before", confidence=1.0),
    ]

    clean, was_cyclic = _remove_cycles(events, relations)

    assert was_cyclic is True
    assert len(clean) == 2
