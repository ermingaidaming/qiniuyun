"""HAR report persistence."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.tables import HARFindingTable, HARReportTable
from app.models.har import HARFinding, HARReport
from app.models.screenplay import Scene, SceneElement


async def save_report(session: AsyncSession, report: HARReport) -> None:
    """Save a HAR report, its findings, and corrected scenes."""
    corrected_json: list[dict[str, Any]] = []
    for scene in report.corrected_scenes:
        corrected_json.append(
            {
                "index": scene.index,
                "setting": scene.setting,
                "location": scene.location,
                "time_of_day": scene.time_of_day,
                "source_chapter": scene.source_chapter,
                "characters": scene.characters,
                "elements": [{"type": e.type, "content": e.content, "character": e.character} for e in scene.elements],
            }
        )

    report_row = HARReportTable(
        id=report.id,
        novel_id=report.novel_id,
        total_scenes=report.total_scenes,
        total_findings=report.total_findings,
        verification_rounds=report.verification_rounds,
        corrected_scenes=corrected_json,
        created_at=report.created_at,
    )
    session.add(report_row)

    for finding in report.findings:
        session.add(
            HARFindingTable(
                id=str(uuid.uuid4()),
                report_id=report.id,
                scene_index=finding.scene_index,
                severity=finding.severity,
                category=finding.category,
                description=finding.description,
                hallucinated_text=finding.hallucinated_text,
                suggested_fix=finding.suggested_fix,
                source_evidence=finding.source_evidence,
            )
        )

    await session.commit()


async def get_report_by_novel(session: AsyncSession, novel_id: str) -> HARReport | None:
    """Get the HAR report for a given novel ID."""
    result = await session.execute(
        select(HARReportTable).where(HARReportTable.novel_id == novel_id).options(selectinload(HARReportTable.findings))
    )
    row = result.scalar_one_or_none()
    if row is None:
        return None
    return _report_from_row(row)


def _report_from_row(row: HARReportTable) -> HARReport:
    """Convert an ORM row to a Pydantic model."""
    corrected_scenes: list[Scene] = []
    for raw in row.corrected_scenes:
        corrected_scenes.append(
            Scene(
                index=raw.get("index", 0),
                setting=raw.get("setting", ""),
                location=raw.get("location", ""),
                time_of_day=raw.get("time_of_day", ""),
                source_chapter=raw.get("source_chapter", 0),
                characters=raw.get("characters", []),
                elements=[
                    SceneElement(
                        type=elem.get("type", "action"),  # type: ignore[arg-type]
                        content=elem.get("content", ""),
                        character=elem.get("character"),
                    )
                    for elem in raw.get("elements", [])
                ],
            )
        )

    return HARReport(
        id=row.id,
        novel_id=row.novel_id,
        total_scenes=row.total_scenes,
        total_findings=row.total_findings,
        findings=[
            HARFinding(
                scene_index=f.scene_index,
                severity=f.severity,  # type: ignore[arg-type]
                category=f.category,  # type: ignore[arg-type]
                description=f.description,
                hallucinated_text=f.hallucinated_text,
                suggested_fix=f.suggested_fix,
                source_evidence=f.source_evidence,
            )
            for f in row.findings
        ],
        corrected_scenes=corrected_scenes,
        verification_rounds=row.verification_rounds,
        created_at=row.created_at,
    )
