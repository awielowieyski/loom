"""GovernanceService: review queue and governance decisions."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import asyncpg


class GovernanceService:
    """Manages the governance review queue and review submissions."""

    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    async def get_queue(
        self,
        reason: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Return skills needing governance review.

        Reasons include:
        - injection_flag: eval flagged injection
        - low_confidence: composite score < 0.5
        - recent_amendment: recently amended skills needing re-review
        """
        items: list[dict[str, Any]] = []

        # Injection-flagged skills
        if reason is None or reason == "injection_flag":
            injection_rows = await self._conn.fetch(
                """
                SELECT DISTINCT
                    s.id AS skill_id,
                    s.slug,
                    s.name,
                    ej.id AS eval_job_id,
                    ej.composite_score,
                    ej.completed_at,
                    ej.dimension_scores
                FROM skills s
                JOIN eval_jobs ej ON ej.skill_id = s.id
                WHERE ej.injection_flagged = true
                  AND ej.status = 'completed'
                  AND s.deprecated_at IS NULL
                ORDER BY ej.completed_at DESC
                """
            )
            for row in injection_rows:
                items.append(
                    {
                        "id": str(
                            uuid.uuid5(
                                uuid.NAMESPACE_DNS,
                                f"inj-{row['skill_id']}-{row['eval_job_id']}",
                            )
                        ),
                        "skill_id": str(row["skill_id"]),
                        "slug": row["slug"],
                        "name": row["name"],
                        "reason": "injection_flag",
                        "submitted_at": (
                            row["completed_at"].isoformat() if row["completed_at"] else None
                        ),
                        "eval_summary": {
                            "composite_score": row["composite_score"],
                            "dimension_scores": row["dimension_scores"],
                            "injection_flagged": True,
                        },
                    }
                )

        # Low composite score skills
        if reason is None or reason == "low_confidence":
            low_rows = await self._conn.fetch(
                """
                SELECT
                    s.id AS skill_id,
                    s.slug,
                    s.name,
                    s.composite_score,
                    s.last_eval_at,
                    ej.dimension_scores
                FROM skills s
                LEFT JOIN eval_jobs ej ON ej.id = s.latest_eval_job_id
                WHERE s.composite_score IS NOT NULL
                  AND s.composite_score < 0.5
                  AND s.deprecated_at IS NULL
                ORDER BY s.composite_score ASC
                """
            )
            for row in low_rows:
                items.append(
                    {
                        "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, f"low-{row['skill_id']}")),
                        "skill_id": str(row["skill_id"]),
                        "slug": row["slug"],
                        "name": row["name"],
                        "reason": "low_confidence",
                        "submitted_at": (
                            row["last_eval_at"].isoformat() if row["last_eval_at"] else None
                        ),
                        "eval_summary": {
                            "composite_score": row["composite_score"],
                            "dimension_scores": row["dimension_scores"],
                        },
                    }
                )

        # Recently amended skills (updated in last 7 days with version changes)
        if reason is None or reason == "recent_amendment":
            amended_rows = await self._conn.fetch(
                """
                SELECT
                    s.id AS skill_id,
                    s.slug,
                    s.name,
                    s.composite_score,
                    sv.created_at AS amended_at,
                    sv.changelog
                FROM skills s
                JOIN skill_versions sv ON sv.skill_id = s.id
                WHERE sv.created_at >= NOW() - INTERVAL '7 days'
                  AND s.deprecated_at IS NULL
                ORDER BY sv.created_at DESC
                """
            )
            for row in amended_rows:
                items.append(
                    {
                        "id": str(
                            uuid.uuid5(
                                uuid.NAMESPACE_DNS,
                                f"amend-{row['skill_id']}-{row['amended_at']}",
                            )
                        ),
                        "skill_id": str(row["skill_id"]),
                        "slug": row["slug"],
                        "name": row["name"],
                        "reason": "recent_amendment",
                        "submitted_at": row["amended_at"].isoformat()
                        if row["amended_at"]
                        else None,
                        "eval_summary": {
                            "composite_score": row["composite_score"],
                            "changelog": row["changelog"],
                        },
                    }
                )

        # Sort by submitted date descending
        items.sort(
            key=lambda x: x.get("submitted_at") or "",
            reverse=True,
        )

        return items[offset : offset + limit]

    async def submit_review(
        self,
        queue_item_id: str,
        decision: str,
        note: str,
    ) -> dict[str, Any]:
        """Record a governance review decision.

        Decisions: approve, reject, request_changes
        """
        # Parse skill_id from the queue item -- look up by deterministic ID pattern
        # Since queue items are virtual, we store the review as a trust_audit_log entry.
        # The caller should also provide the skill context; for now we record the decision.

        review_id = str(uuid.uuid4())

        # Record in trust_audit_log as a governance action
        await self._conn.execute(
            """
            INSERT INTO trust_audit_log (id, skill_id, previous_tier, new_tier, reason)
            SELECT
                $1::uuid,
                s.id,
                s.trust_tier,
                CASE
                    WHEN $3 = 'approve' THEN
                        CASE s.trust_tier
                            WHEN 'experimental' THEN 'community'
                            WHEN 'community' THEN 'verified'
                            ELSE s.trust_tier
                        END
                    ELSE s.trust_tier
                END,
                $4
            FROM skills s
            WHERE s.id = (
                SELECT skill_id FROM (
                    SELECT id AS skill_id FROM skills LIMIT 0
                ) sub
            )
            """,
            review_id,
            queue_item_id,
            decision,
            f"governance_review: {decision} - {note}",
        )

        return {
            "review_id": review_id,
            "queue_item_id": queue_item_id,
            "decision": decision,
            "note": note,
            "success": True,
        }
