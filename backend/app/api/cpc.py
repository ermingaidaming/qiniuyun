"""CPC (Causal Plot Graph) API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.cpc import BuildCpcRequest, CausalGraph
from app.services import cpc_service, novel_service

router = APIRouter(prefix="/cpc", tags=["cpc"])


@router.post("/build")
async def build_cpc(body: BuildCpcRequest) -> CausalGraph:
    """Build a CPC causal graph for a novel."""
    novel = await novel_service.get_novel(body.novel_id)
    if novel is None:
        raise HTTPException(status_code=404, detail="Novel not found")
    return await cpc_service.build_causal_graph(novel)


@router.get("/{novel_id}/graph")
async def get_cpc_graph(novel_id: str) -> CausalGraph:
    """Get the CPC causal graph for a novel."""
    graph = await cpc_service.get_graph(novel_id)
    if graph is None:
        raise HTTPException(status_code=404, detail="CPC graph not found")
    return graph
