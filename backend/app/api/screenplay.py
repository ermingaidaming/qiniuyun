from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from app.models.screenplay import Screenplay
from app.services import novel_service, screenplay_service

router = APIRouter(tags=["screenplay"])


class GenerateRequest(BaseModel):
    novel_id: str

    model_config = ConfigDict(extra="forbid")


@router.post("/screenplay/generate")
async def generate_screenplay(req: GenerateRequest) -> Screenplay:
    """Generate a screenplay from a previously uploaded novel."""
    novel = await novel_service.get_novel(req.novel_id)
    if novel is None:
        raise HTTPException(status_code=404, detail="Novel not found")

    # Check if already generated
    existing = await screenplay_service.get_screenplay_by_novel(req.novel_id)
    if existing:
        return existing

    screenplay = await screenplay_service.generate_screenplay(novel)
    return screenplay


@router.get("/screenplay/{screenplay_id}")
async def get_screenplay(screenplay_id: str) -> Screenplay:
    """Get a generated screenplay by ID."""
    screenplay = await screenplay_service.get_screenplay(screenplay_id)
    if screenplay is None:
        raise HTTPException(status_code=404, detail="Screenplay not found")
    return screenplay
