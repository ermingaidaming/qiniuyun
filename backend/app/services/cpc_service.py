"""CPC (Causal Plot Graph) service — event extraction, relation identification,
and DAG construction driven by LLM calls.

Pipeline:
  chapters → extract_events (LLM) → identify_relations (LLM) → remove_cycles → DAG
"""

from __future__ import annotations

import uuid
from collections import defaultdict, deque
from typing import Any

from app.db.engine import async_session
from app.db.repository.cpc import (
    get_causal_graph_by_novel as _db_get_graph,
)
from app.db.repository.cpc import save_causal_graph as _db_save_graph
from app.models.cpc import CausalGraph, CausalRelation, Event
from app.models.novel import Novel
from app.services.llm_service import extract_events_from_chapter, identify_event_relations


async def build_causal_graph(novel: Novel) -> CausalGraph:
    """Build a CPC causal graph for a novel.

    1. Extract events from each chapter via LLM
    2. Identify causal / temporal relationships via LLM
    3. Remove cycles to ensure DAG validity
    4. Persist and return
    """
    # ── 1. Event Extraction ──────────────────────────────────────────
    all_events: list[Event] = []
    event_idx = 0

    for chapter in novel.chapters:
        try:
            raw_events = await extract_events_from_chapter(chapter.title, chapter.content)
            for raw in raw_events:
                event_idx += 1
                all_events.append(
                    Event(
                        id=_event_id(novel.id, event_idx),
                        index=event_idx,
                        chapter_index=chapter.index,
                        description=raw.get("description", ""),
                        characters=raw.get("characters", []),
                        location=raw.get("location", ""),
                        time=raw.get("time", ""),
                    )
                )
        except Exception:
            # If LLM fails for a chapter, create a fallback event
            event_idx += 1
            all_events.append(
                Event(
                    id=_event_id(novel.id, event_idx),
                    index=event_idx,
                    chapter_index=chapter.index,
                    description=f"第{chapter.index}章: {chapter.title}",
                    characters=[],
                )
            )

    if not all_events:
        # Empty graph for novels with no extractable events
        graph = CausalGraph(id=str(uuid.uuid4()), novel_id=novel.id, events=[], relations=[], dag_valid=True)
        async with async_session() as session:
            await _db_save_graph(session, graph)
        return graph

    # ── 2. Relation Identification ───────────────────────────────────
    event_summaries = [
        {
            "id": e.id,
            "index": e.index,
            "chapter": e.chapter_index,
            "description": e.description,
            "characters": e.characters,
            "location": e.location,
            "time": e.time,
        }
        for e in all_events
    ]

    raw_relations: list[dict[str, Any]] = []
    try:
        raw_relations = await identify_event_relations(event_summaries)
    except Exception:
        raw_relations = []

    relations: list[CausalRelation] = []
    for raw in raw_relations:
        relations.append(
            CausalRelation(
                id=str(uuid.uuid4()),
                source_event_id=str(raw.get("source_event_id", "")),
                target_event_id=str(raw.get("target_event_id", "")),
                relation_type=str(raw.get("relation_type", "before")),  # type: ignore[arg-type]
                confidence=float(raw.get("confidence", 1.0)),
            )
        )

    # ── 3. Cycle Removal ─────────────────────────────────────────────
    relations, dag_valid = _remove_cycles(all_events, relations)

    # ── 4. Persist ───────────────────────────────────────────────────
    graph = CausalGraph(
        id=str(uuid.uuid4()),
        novel_id=novel.id,
        events=all_events,
        relations=relations,
        dag_valid=dag_valid,
    )
    async with async_session() as session:
        await _db_save_graph(session, graph)

    return graph


async def get_graph(novel_id: str) -> CausalGraph | None:
    """Get the causal graph for a novel."""
    async with async_session() as session:
        return await _db_get_graph(session, novel_id)


def _event_id(novel_id: str, index: int) -> str:
    """Deterministic event ID."""
    short = novel_id.replace("-", "")[:12]
    return f"{short}-e{index}"


# ── Cycle Removal (Kahn topological sort + greedy edge removal) ─────


def _remove_cycles(
    events: list[Event], relations: list[CausalRelation]
) -> tuple[list[CausalRelation], bool]:
    """Remove cycles to guarantee a DAG. Returns (clean_relations, was_cyclic)."""
    if not relations:
        return relations, True

    event_ids = {e.id for e in events}

    # Filter to valid event references & sort by confidence descending
    valid = [r for r in relations if r.source_event_id in event_ids and r.target_event_id in event_ids]
    valid.sort(key=lambda r: r.confidence, reverse=True)

    # Build adjacency and in-degree
    adj: dict[str, list[str]] = defaultdict(list)
    in_degree: dict[str, int] = {e.id: 0 for e in events}

    for r in valid:
        adj[r.source_event_id].append(r.target_event_id)
        in_degree[r.target_event_id] = in_degree.get(r.target_event_id, 0) + 1

    # Kahn's algorithm
    queue: deque[str] = deque(eid for eid, deg in in_degree.items() if deg == 0)
    topo_order: list[str] = []
    kept_edges: set[tuple[str, str]] = set()

    # Track edges we can use
    edge_map: dict[tuple[str, str], CausalRelation] = {}
    for r in valid:
        key = (r.source_event_id, r.target_event_id)
        # If duplicate edges exist, keep the higher confidence one
        if key not in edge_map or r.confidence > edge_map[key].confidence:
            edge_map[key] = r

    while queue:
        node = queue.popleft()
        topo_order.append(node)

        for neighbor in adj[node]:
            # Only consider this edge if it's in our edge map
            if (node, neighbor) in edge_map:
                kept_edges.add((node, neighbor))
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    # Check if all nodes were processed
    all_processed = len(topo_order) == len(event_ids)

    # If not all processed, greedily remove edges until DAG
    if not all_processed:
        # Greedy: remove edges from lowest confidence, retry Kahn
        remaining = [r for r in valid if (r.source_event_id, r.target_event_id) not in kept_edges]
        remaining.sort(key=lambda r: r.confidence, reverse=True)  # highest first

        for r in remaining:
            if (r.source_event_id, r.target_event_id) in kept_edges:
                continue
            # Try adding this edge — if it creates a cycle, skip it
            if _would_create_cycle(kept_edges, r.source_event_id, r.target_event_id, event_ids):
                continue
            kept_edges.add((r.source_event_id, r.target_event_id))

    # Reconstruct relation list from kept edges
    clean_relations = [edge_map[key] for key in kept_edges if key in edge_map]

    return clean_relations, all_processed


def _would_create_cycle(
    kept: set[tuple[str, str]], src: str, tgt: str, event_ids: set[str]
) -> bool:
    """Check if adding edge src→tgt would create a cycle."""
    # Build adjacency from kept edges + the candidate
    adj: dict[str, list[str]] = defaultdict(list)
    for s, t in kept:
        adj[s].append(t)
    adj[src].append(tgt)

    # DFS from tgt to see if src is reachable (would mean a cycle)
    visited: set[str] = set()
    stack = [tgt]
    while stack:
        node = stack.pop()
        if node == src:
            return True
        if node in visited:
            continue
        visited.add(node)
        stack.extend(adj.get(node, []))

    return False
