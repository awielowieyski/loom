"""Drift detection for score and model changes across evaluations."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from loom.models.drift import DriftReport, ModelDriftReport

if TYPE_CHECKING:
    import uuid as uuid_mod

logger = logging.getLogger(__name__)


class DriftDetector:
    """Detects score and model drift by comparing scores across versions."""

    def __init__(
        self,
        eval_repo: Any,
        drift_threshold: float = 0.15,
        model_drift_threshold: float = 0.10,
    ) -> None:
        self._eval_repo = eval_repo
        self._drift_threshold = drift_threshold
        self._model_drift_threshold = model_drift_threshold

    async def check_score_drift(
        self,
        skill_id: uuid_mod.UUID,
        new_eval_job_id: uuid_mod.UUID,
    ) -> DriftReport | None:
        """Compare new score to previous. Returns report if drift exceeds threshold."""
        new_job = await self._eval_repo.get_eval_job(new_eval_job_id)
        if new_job is None or new_job.composite_score is None:
            return None

        # Get the two most recent completed jobs for this skill
        jobs = await self._eval_repo.get_recent_completed_jobs(skill_id, limit=2)
        if len(jobs) < 2:
            return None

        # jobs are ordered newest-first; find the one that isn't the new job
        old_job = None
        for job in jobs:
            if job.id != new_eval_job_id:
                old_job = job
                break

        if old_job is None or old_job.composite_score is None:
            return None

        delta = abs(new_job.composite_score - old_job.composite_score)
        exceeds = delta > self._drift_threshold

        if not exceeds:
            return None

        return DriftReport(
            skill_id=skill_id,
            old_score=old_job.composite_score,
            new_score=new_job.composite_score,
            delta=delta,
            exceeds_threshold=True,
        )

    async def check_model_drift(
        self,
        current_model: str,
        sample_size: int = 20,
    ) -> ModelDriftReport | None:
        """Check if model change caused systematic score drift across a sample.

        Looks at recent completed jobs, groups by evaluator_version, and
        computes mean absolute deviation for skills assessed by both versions.
        """
        jobs = await self._eval_repo.get_recent_completed_jobs_all(limit=sample_size * 2)
        if not jobs:
            return None

        # Group by evaluator_version
        by_version: dict[str, dict[uuid_mod.UUID, float]] = {}
        for job in jobs:
            if job.composite_score is None:
                continue
            version = job.evaluator_version
            if version not in by_version:
                by_version[version] = {}
            # Keep only the most recent score per skill per version
            if job.skill_id not in by_version[version]:
                by_version[version][job.skill_id] = job.composite_score

        versions = list(by_version.keys())
        if len(versions) < 2:
            return None

        # Compare the two most recent versions
        old_version = versions[-1] if versions[-1] != current_model else versions[0]
        new_version = current_model

        if old_version == new_version:
            return None

        old_scores = by_version.get(old_version, {})
        new_scores = by_version.get(new_version, {})

        # Find overlapping skills
        common_skills = set(old_scores.keys()) & set(new_scores.keys())
        if not common_skills:
            return None

        deltas: list[DriftReport] = []
        abs_deviations: list[float] = []
        for sid in common_skills:
            old_s = old_scores[sid]
            new_s = new_scores[sid]
            d = abs(new_s - old_s)
            abs_deviations.append(d)
            deltas.append(
                DriftReport(
                    skill_id=sid,
                    old_score=old_s,
                    new_score=new_s,
                    delta=d,
                    exceeds_threshold=d > self._drift_threshold,
                )
            )

        mad = sum(abs_deviations) / len(abs_deviations)
        exceeds = mad > self._model_drift_threshold

        return ModelDriftReport(
            old_model=old_version,
            new_model=new_version,
            mean_absolute_deviation=mad,
            exceeds_threshold=exceeds,
            sample_size=len(common_skills),
            per_skill_deltas=deltas,
        )
