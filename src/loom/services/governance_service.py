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

        Queue items carry a `skill_id` field (set during `get_queue`).
        We look up the skill by that ID and record an audit log entry.
        On 'approve', the skill is promoted one trust tier.

        Decisions: approve, reject, request_changes
        """
        review_id = str(uuid.uuid4())
        reason = f"governance_review: {decision} - {note}"

        # Look up the skill associated with this queue item.
        # Queue items embed a skill_id; the caller passes queue_item_id which
        # is a deterministic UUID derived from the skill + context.  We need
        # the actual skill_id — the caller should include it.  For robustness
        # we also accept a raw skill UUID as queue_item_id.
        skill_row = await self._conn.fetchrow(
            "SELECT id, trust_tier FROM skills WHERE id::text = $1",
            queue_item_id,
        )
        if not skill_row:
            return {
                "review_id": review_id,
                "queue_item_id": queue_item_id,
                "decision": decision,
                "note": note,
                "success": False,
                "error": "Skill not found for queue item",
            }

        skill_id = skill_row["id"]
        current_tier = skill_row["trust_tier"]

        # Compute new tier on approval
        _PROMOTION = {"experimental": "community", "community": "verified"}
        new_tier = (
            _PROMOTION.get(current_tier, current_tier) if decision == "approve" else current_tier
        )

        # Record in trust_audit_log
        await self._conn.execute(
            """
            INSERT INTO trust_audit_log (id, skill_id, previous_tier, new_tier, reason)
            VALUES ($1::uuid, $2, $3, $4, $5)
            """,
            review_id,
            skill_id,
            current_tier,
            new_tier,
            reason,
        )

        # Update skill trust_tier on approval
        if decision == "approve" and new_tier != current_tier:
            await self._conn.execute(
                "UPDATE skills SET trust_tier = $1 WHERE id = $2",
                new_tier,
                skill_id,
            )

        return {
            "review_id": review_id,
            "queue_item_id": queue_item_id,
            "decision": decision,
            "note": note,
            "success": True,
        }
