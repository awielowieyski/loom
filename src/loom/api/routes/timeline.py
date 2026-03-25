"""Skill timeline API route."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003 — needed at runtime by Pydantic
from typing import Annotated

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from loom.api.deps import get_conn, get_skill_repo
from loom.api.middleware import verify_api_key
from loom.db.repositories.skill_repo import SkillRepo  # noqa: TC001 — FastAPI needs this at runtime

router = APIRouter(prefix="/api/v1", tags=["timeline"])

_TRUST_RANK = {"experimental": 0, "community": 1, "verified": 2}


class TimelineEvent(BaseModel):
    """A single event in a skill's lifecycle timeline."""

    timestamp: datetime
    event_type: str
    detail: str


class TimelineResponse(BaseModel):
    """Response for the skill timeline endpoint."""

    events: list[TimelineEvent]


async def _build_timeline(
    conn: asyncpg.Connection,
    skill_id: str,
    skill_name: str,
    created_at: datetime | None,
) -> list[TimelineEvent]:
    """Aggregate events from multiple tables into a unified timeline."""
    events: list[TimelineEvent] = []

    # 1. Skill submission
    if created_at is not None:
        events.append(
            TimelineEvent(
                timestamp=created_at,
                event_type="submitted",
                detail=f"Skill '{skill_name}' submitted",
            )
        )

    # 2. Eval completions
    eval_rows = await conn.fetch(
        """
        SELECT id, composite_score, completed_at
        FROM eval_jobs
        WHERE skill_id = $1 AND status = 'completed' AND completed_at IS NOT NULL
        ORDER BY completed_at
        """,
        skill_id,
    )
    for row in eval_rows:
        events.append(
            TimelineEvent(
                timestamp=row["completed_at"],
                event_type="eval_completed",
                detail=f"Evaluation completed (score: {row['composite_score']})",
            )
        )

    # 3. Trust tier changes
    trust_rows = await conn.fetch(
        """
        SELECT previous_tier, new_tier, reason, created_at
        FROM trust_audit_log
        WHERE skill_id = $1
        ORDER BY created_at
        """,
        skill_id,
    )
    for row in trust_rows:
        prev_rank = _TRUST_RANK.get(row["previous_tier"], 0)
        new_rank = _TRUST_RANK.get(row["new_tier"], 0)
        event_type = "promoted" if new_rank > prev_rank else "demoted"
        events.append(
            TimelineEvent(
                timestamp=row["created_at"],
                event_type=event_type,
                detail=(
                    f"Trust tier {row['previous_tier']} -> {row['new_tier']} ({row['reason']})"
                ),
            )
        )

    # 4. Skill versions if table exists
    try:
        version_rows = await conn.fetch(
            """
            SELECT version, created_at, changelog
            FROM skill_versions
            WHERE skill_id = $1
            ORDER BY created_at
            """,
            skill_id,
        )
        for row in version_rows:
            changelog = row.get("changelog") or "New version"
            events.append(
                TimelineEvent(
                    timestamp=row["created_at"],
                    event_type="version",
                    detail=f"Version {row['version']}: {changelog}",
                )
            )
    except asyncpg.UndefinedTableError:
        pass  # skill_versions table may not exist yet

    # Sort chronologically (oldest first)
    events.sort(key=lambda e: e.timestamp)
    return events


@router.get(
    "/skills/{slug}/timeline",
    response_model=TimelineResponse,
)
async def get_skill_timeline(
    slug: str,
    _: Annotated[str | None, Depends(verify_api_key)],
    skill_repo: Annotated[SkillRepo, Depends(get_skill_repo)],
    conn: Annotated[asyncpg.Connection, Depends(get_conn)],
) -> TimelineResponse:
    """Return a unified, chronologically sorted timeline for a skill."""
    skill = await skill_repo.get_by_slug(slug)
    if skill is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill {slug!r} not found",
        )
    events = await _build_timeline(
        conn,
        skill_id=str(skill.id),
        skill_name=skill.name,
        created_at=skill.created_at,
    )
    return TimelineResponse(events=events)
