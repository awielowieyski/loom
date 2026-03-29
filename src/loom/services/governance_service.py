"""GovernanceService: review queue and governance decisions."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from loom.db.repositories.pipeline_run_repo import PipelineRunRepo
from loom.db.repositories.service_metadata_repo import ServiceMetadataRepo
from loom.models.common import LifecycleState, TrustTier
from loom.services.service_metadata_extractor import extract_service_metadata

if TYPE_CHECKING:
    import asyncpg


class GovernanceService:
    """Manages the governance review queue and review submissions."""

    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    async def get_queue(
        self,
        reason: str | None = None,
        stage: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Return governance work items grouped by lifecycle stage."""
        rows = await self._conn.fetch(
            """
            SELECT
                s.id AS skill_id,
                s.slug,
                s.name,
                s.display_name,
                s.lifecycle_state,
                s.trust_tier,
                s.provenance_summary,
                s.authorship_status,
                s.canonicalization_level,
                s.current_version_id,
                s.published_version_id,
                s.composite_score,
                s.eval_status,
                s.updated_at,
                s.created_at,
                ej.dimension_scores,
                ej.injection_flagged,
                sv.changelog
            FROM skills s
            LEFT JOIN eval_jobs ej ON ej.id = s.latest_eval_job_id
            LEFT JOIN LATERAL (
                SELECT changelog
                FROM skill_versions
                WHERE skill_id = s.id
                ORDER BY created_at DESC
                LIMIT 1
            ) sv ON true
            WHERE s.deprecated_at IS NULL
            ORDER BY s.updated_at DESC NULLS LAST, s.created_at DESC
            """
        )

        items: list[dict[str, Any]] = []
        for row in rows:
            lifecycle_state = row["lifecycle_state"]
            stage_name = self._stage_for_lifecycle(lifecycle_state)
            if stage_name is None:
                continue

            reason_name = self._reason_for_row(
                injection_flagged=bool(row["injection_flagged"]),
                composite_score=row["composite_score"],
                changelog=row["changelog"],
                lifecycle_state=lifecycle_state,
            )
            if reason is not None and reason_name != reason:
                continue
            if stage is not None and stage_name != stage:
                continue

            submitted_at = row["updated_at"] or row["created_at"]
            items.append(
                {
                    "id": str(
                        uuid.uuid5(
                            uuid.NAMESPACE_DNS,
                            f"{stage_name}-{row['skill_id']}-{submitted_at}",
                        )
                    ),
                    "skill_id": str(row["skill_id"]),
                    "slug": row["slug"],
                    "name": row["display_name"] or row["name"],
                    "stage": stage_name,
                    "reason": reason_name,
                    "submitted_at": submitted_at.isoformat() if submitted_at else None,
                    "lifecycle_state": lifecycle_state,
                    "trust_tier": row["trust_tier"],
                    "authorship_status": row["authorship_status"],
                    "canonicalization_level": row["canonicalization_level"],
                    "provenance_summary": row["provenance_summary"] or {},
                    "current_version_id": str(row["current_version_id"])
                    if row["current_version_id"]
                    else None,
                    "published_version_id": str(row["published_version_id"])
                    if row["published_version_id"]
                    else None,
                    "eval_summary": {
                        "composite_score": row["composite_score"],
                        "dimension_scores": row["dimension_scores"],
                        "injection_flagged": bool(row["injection_flagged"]),
                        "changelog": row["changelog"],
                        "eval_status": row["eval_status"],
                    },
                }
            )

        items.sort(key=lambda x: x.get("submitted_at") or "", reverse=True)
        return items[offset : offset + limit]

    @staticmethod
    def _stage_for_lifecycle(lifecycle_state: str | None) -> str | None:
        if lifecycle_state == "quarantined":
            return "quarantine"
        if lifecycle_state in {"canonicalizing", "review"}:
            return "canonicalization"
        if lifecycle_state == "deduplicating":
            return "dedup"
        if lifecycle_state == "evaluating":
            return "evaluation"
        if lifecycle_state == "published":
            return "publication"
        return None

    @staticmethod
    def _reason_for_row(
        *,
        injection_flagged: bool,
        composite_score: float | None,
        changelog: str | None,
        lifecycle_state: str | None,
    ) -> str:
        if injection_flagged:
            return "injection_flag"
        if lifecycle_state == "quarantined":
            return "recent_amendment"
        if composite_score is not None and composite_score < 0.5:
            return "low_confidence"
        if changelog:
            return "recent_amendment"
        return "low_confidence"

    @staticmethod
    def _next_lifecycle_for_approval(current: str) -> str:
        transitions = {
            LifecycleState.QUARANTINED.value: LifecycleState.CANONICALIZING.value,
            LifecycleState.CANONICALIZING.value: LifecycleState.DEDUPLICATING.value,
            LifecycleState.REVIEW.value: LifecycleState.DEDUPLICATING.value,
            LifecycleState.DEDUPLICATING.value: LifecycleState.EVALUATING.value,
            LifecycleState.EVALUATING.value: LifecycleState.PUBLISHED.value,
        }
        return transitions.get(current, current)

    async def request_rerun(
        self,
        *,
        skill_id: str,
        request_mode: str,
        note: str,
        requested_via: str = "dashboard",
    ) -> dict[str, Any]:
        """Create a rerun request and execute immediately when supported."""
        valid_modes = {"canonicalize", "evaluate", "full_pipeline"}
        if request_mode not in valid_modes:
            return {
                "success": False,
                "error": f"Unsupported rerun mode: {request_mode}",
            }

        skill_row = await self._conn.fetchrow(
            """
            SELECT id, slug, content, source_uri, current_version_id
            FROM skills
            WHERE id::text = $1
            """,
            skill_id,
        )
        if skill_row is None:
            return {
                "success": False,
                "error": "Skill not found",
            }

        repo = PipelineRunRepo(self._conn)
        initial_status = "running" if request_mode == "canonicalize" else "pending"
        request = await repo.create(
            skill_id=skill_row["id"],
            artifact_id=None,
            request_mode=request_mode,
            requested_via=requested_via,
            note=note,
            status=initial_status,
        )

        if request_mode != "canonicalize":
            return {
                "success": True,
                "request": request.model_dump(mode="json"),
                "message": (
                    "Rerun request queued. Automatic execution for this mode is not yet "
                    "wired into the backend worker."
                ),
            }

        current_version_id = skill_row["current_version_id"]
        if current_version_id is None:
            updated = await repo.update_status(
                request.id,
                status="failed",
                result_summary={"error": "Skill has no current version to canonicalize"},
            )
            return {
                "success": False,
                "request": updated.model_dump(mode="json") if updated else None,
                "error": "Skill has no current version to canonicalize",
            }

        dependencies, pricing_facts, setup_requirements = extract_service_metadata(
            skill_content=skill_row["content"],
            source_uri=skill_row["source_uri"],
        )
        service_repo = ServiceMetadataRepo(self._conn)
        await service_repo.replace_skill_version_metadata(
            skill_version_id=current_version_id,
            dependencies=dependencies,
            pricing_facts=pricing_facts,
            setup_requirements=setup_requirements,
        )
        await self._conn.execute(
            "UPDATE skills SET updated_at = now() WHERE id = $1", skill_row["id"]
        )
        updated = await repo.update_status(
            request.id,
            status="completed",
            result_summary={
                "mode": request_mode,
                "service_count": len(dependencies),
                "pricing_fact_count": len(pricing_facts),
                "setup_requirement_count": len(setup_requirements),
            },
        )
        return {
            "success": True,
            "request": updated.model_dump(mode="json")
            if updated
            else request.model_dump(mode="json"),
            "message": "Canonicalization rerun completed.",
        }

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
            "SELECT id, trust_tier, lifecycle_state FROM skills WHERE id::text = $1",
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
        current_lifecycle = skill_row["lifecycle_state"]

        promotion = {
            TrustTier.UNVETTED.value: TrustTier.EXPERIMENTAL.value,
            TrustTier.EXPERIMENTAL.value: TrustTier.COMMUNITY.value,
            TrustTier.COMMUNITY.value: TrustTier.VERIFIED.value,
        }

        new_lifecycle = current_lifecycle
        new_tier = current_tier

        if decision == "approve":
            new_lifecycle = self._next_lifecycle_for_approval(current_lifecycle)
            if current_lifecycle == LifecycleState.PUBLISHED.value:
                new_tier = promotion.get(current_tier, current_tier)
            elif (
                new_lifecycle == LifecycleState.PUBLISHED.value
                and current_tier == TrustTier.UNVETTED.value
            ):
                new_tier = TrustTier.EXPERIMENTAL.value
        elif decision == "request_changes":
            new_lifecycle = LifecycleState.REVIEW.value
        elif decision == "reject":
            new_lifecycle = LifecycleState.REJECTED.value

        if decision in {"approve", "request_changes", "reject"}:
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

        if new_lifecycle != current_lifecycle or new_tier != current_tier:
            await self._conn.execute(
                "UPDATE skills SET lifecycle_state = $1, trust_tier = $2 WHERE id = $3",
                new_lifecycle,
                new_tier,
                skill_id,
            )

        return {
            "review_id": review_id,
            "queue_item_id": queue_item_id,
            "decision": decision,
            "note": note,
            "success": True,
            "lifecycle_state": new_lifecycle,
            "trust_tier": new_tier,
        }
