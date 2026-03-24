"""Usage signal coordination — report ingestion, aggregate retrieval, deprecation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from loom.models.usage import UsageReport, UsageReportCreate, UsageStats

if TYPE_CHECKING:
    from loom.db.repositories.skill_repo import SkillRepo
    from loom.db.repositories.usage_repo import UsageRepo


class UsageService:
    """Handles usage report ingestion, aggregate retrieval, and deprecation."""

    def __init__(
        self,
        usage_repo: UsageRepo,
        skill_repo: SkillRepo,
    ) -> None:
        self._usage_repo = usage_repo
        self._skill_repo = skill_repo

    async def report_usage(self, report: UsageReportCreate) -> UsageReport:
        """Record a usage outcome. Idempotent on idempotency_key."""
        skill = await self._skill_repo.get_by_slug(report.skill_slug)
        if skill is None:
            raise ValueError(f"Skill not found: {report.skill_slug}")

        usage_report = await self._usage_repo.create_usage_report(
            skill_id=skill.id,
            skill_version=report.skill_version,
            outcome=report.outcome.value,
            runtime_ms=report.runtime_ms,
            context_hash=report.context_hash,
            failure_reason=report.failure_reason,
            idempotency_key=report.idempotency_key,
        )

        await self._skill_repo.increment_resolution_count(skill.id)
        await self._skill_repo.clear_stale(skill.id)

        return usage_report

    async def get_usage_stats(self, skill_slug: str) -> UsageStats:
        """Return aggregate usage statistics for all window types."""
        skill = await self._skill_repo.get_by_slug(skill_slug)
        if skill is None:
            raise ValueError(f"Skill not found: {skill_slug}")

        aggregates = await self._usage_repo.get_aggregates_for_skill(skill.id)
        return UsageStats(slug=skill_slug, aggregates=aggregates)

    async def deprecate_skill(self, slug: str, successor_slug: str | None = None) -> dict[str, Any]:
        """Mark a skill as deprecated with optional successor."""
        skill = await self._skill_repo.get_by_slug(slug)
        if skill is None:
            raise ValueError(f"Skill not found: {slug}")

        if successor_slug is not None:
            successor = await self._skill_repo.get_by_slug(successor_slug)
            if successor is None:
                raise ValueError(f"Successor skill not found: {successor_slug}")

        await self._skill_repo.mark_deprecated(skill.id, successor_slug)
        return {"slug": slug, "deprecated": True, "successor_slug": successor_slug}

    async def check_staleness(self, staleness_window_days: int = 90) -> list[str]:
        """Find and mark stale skills (0 resolutions in window). Returns marked skill IDs."""
        stale_ids = await self._skill_repo.get_stale_candidates(staleness_window_days)
        for skill_id in stale_ids:
            await self._skill_repo.mark_stale(skill_id)
        return [str(sid) for sid in stale_ids]
