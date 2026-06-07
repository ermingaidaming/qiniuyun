"""CPC / CausalGraph repository — DB ↔ Pydantic conversions."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.tables import CausalGraphTable, CausalRelationTable, EventTable
from app.models.cpc import CausalGraph, CausalRelation, Event


async def save_causal_graph(session: AsyncSession, graph: CausalGraph) -> None:
    """Insert a CPC causal graph with its events and relations."""
    row = CausalGraphTable(
        id=graph.id,
        novel_id=graph.novel_id,
        dag_valid=graph.dag_valid,
        created_at=graph.created_at,
    )
    for ev in graph.events:
        row.events.append(
            EventTable(
                id=ev.id,
                index=ev.index,
                chapter_index=ev.chapter_index,
                description=ev.description,
                characters=ev.characters,
                location=ev.location,
                time=ev.time,
            )
        )
    for rel in graph.relations:
        row.relations.append(
            CausalRelationTable(
                id=rel.id,
                source_event_id=rel.source_event_id,
                target_event_id=rel.target_event_id,
                relation_type=rel.relation_type,
                confidence=rel.confidence,
            )
        )
    session.add(row)
    await session.commit()


async def get_causal_graph(session: AsyncSession, graph_id: str) -> CausalGraph | None:
    """Fetch a causal graph by its ID."""
    stmt = select(CausalGraphTable).where(CausalGraphTable.id == graph_id)
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    if row is None:
        return None
    return _graph_from_row(row)


async def get_causal_graph_by_novel(session: AsyncSession, novel_id: str) -> CausalGraph | None:
    """Fetch the causal graph for a given novel, ordered by index."""
    stmt = select(CausalGraphTable).where(CausalGraphTable.novel_id == novel_id)
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    if row is None:
        return None
    return _graph_from_row(row)


def _graph_from_row(row: CausalGraphTable) -> CausalGraph:
    """Convert an ORM row into a Pydantic CausalGraph model."""
    return CausalGraph(
        id=row.id,
        novel_id=row.novel_id,
        dag_valid=row.dag_valid,
        created_at=row.created_at,
        events=sorted(
            (
                Event(
                    id=e.id,
                    index=e.index,
                    chapter_index=e.chapter_index,
                    description=e.description,
                    characters=e.characters,
                    location=e.location,
                    time=e.time,
                )
                for e in row.events
            ),
            key=lambda e: e.index,
        ),
        relations=[
            CausalRelation(
                id=r.id,
                source_event_id=r.source_event_id,
                target_event_id=r.target_event_id,
                relation_type=r.relation_type,  # type: ignore[arg-type]
                confidence=r.confidence,
            )
            for r in row.relations
        ],
    )
