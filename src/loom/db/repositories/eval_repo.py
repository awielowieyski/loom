"""Eval repository with raw asyncpg SQL."""

import json
import uuid as uuid_mod
from typing import Any

import asyncpg

from loom.models.eval import EvalDimensionRun, EvalJob, TrustAuditEntry

_EVAL_JOB_COLUMNS = (
    "id, skill_id, skill_version, content_hash, trigger_type, status, "
    "structural_report, composite_score, dimension_scores, dimension_confidence, "
    "injection_flagged, sandbox_passed, overall_confidence, evaluator_version, "
    "behavioral_score, started_at, completed_at, created_at"
)

_DIMENSION_RUN_COLUMNS = (
    "id, eval_job_id, dimension, run_index, score, evidence, "
    "injection_detected, injection_detail, confidence, prompt_variant, "
    "model_id, latency_ms, created_at"
)

_TRUST_AUDIT_COLUMNS = (
    "id, skill_id, previous_tier, new_tier, reason, eval_job_id, promoted_by, created_at"
)


def _row_to_eval_job(row: asyncpg.Record) -> EvalJob:
    d = dict(row)
    # asyncpg returns jsonb as strings
    for key in ("structural_report", "dimension_scores", "dimension_confidence"):
        if isinstance(d.get(key), str):
            d[key] = json.loads(d[key])
    return EvalJob(**d)


def _row_to_dimension_run(row: asyncpg.Record) -> EvalDimensionRun:
    d = dict(row)
    # asyncpg returns jsonb as strings
    for key in ("evidence",):
        if isinstance(d.get(key), str):
            d[key] = json.loads(d[key])
    return EvalDimensionRun(**d)


def _row_to_trust_audit_entry(row: asyncpg.Record) -> TrustAuditEntry:
    return TrustAuditEntry(**dict(row))


class EvalRepo:
    """Repository for evaluation pipeline persistence."""

    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    async def create_eval_job(
        self,
        *,
        skill_id: uuid_mod.UUID,
        skill_version: str,
        content_hash: str,
        trigger_type: str,
        evaluator_version: str,
    ) -> EvalJob:
        """Insert a new eval job and return it."""
        row = await self._conn.fetchrow(
            f"""
            INSERT INTO eval_jobs (
                skill_id, skill_version, content_hash, trigger_type, evaluator_version
            ) VALUES ($1, $2, $3, $4, $5)
            RETURNING {_EVAL_JOB_COLUMNS}
            """,
            skill_id,
            skill_version,
            content_hash,
            trigger_type,
            evaluator_version,
        )
        return _row_to_eval_job(row)

    async def get_eval_job(self, job_id: uuid_mod.UUID) -> EvalJob | None:
        """Return an eval job by id."""
        row = await self._conn.fetchrow(
            f"SELECT {_EVAL_JOB_COLUMNS} FROM eval_jobs WHERE id = $1",
            job_id,
        )
        if row is None:
            return None
        return _row_to_eval_job(row)

    async def update_eval_job(
        self,
        job_id: uuid_mod.UUID,
        *,
        status: str | None = None,
        content_hash: str | None = None,
        structural_report: dict[str, Any] | None = None,
        composite_score: float | None = None,
        dimension_scores: dict[str, float] | None = None,
        dimension_confidence: dict[str, float] | None = None,
        injection_flagged: bool | None = None,
        sandbox_passed: bool | None = None,
        overall_confidence: float | None = None,
        behavioral_score: float | None = None,
        started_at: Any | None = None,
        completed_at: Any | None = None,
    ) -> EvalJob | None:
        """UPDATE eval_jobs SET ... WHERE id = $1, RETURNING *."""
        set_parts: list[str] = []
        params: list[Any] = [job_id]

        def _add(field: str, value: object, *, cast: str = "") -> None:
            if value is not None:
                params.append(value)
                set_parts.append(f"{field} = ${len(params)}{cast}")

        def _add_json(field: str, value: dict[str, Any] | None) -> None:
            if value is not None:
                params.append(json.dumps(value))
                set_parts.append(f"{field} = ${len(params)}::jsonb")

        _add("status", status)
        _add("content_hash", content_hash)
        _add_json("structural_report", structural_report)
        _add("composite_score", composite_score)
        _add_json("dimension_scores", dimension_scores)
        _add_json("dimension_confidence", dimension_confidence)
        _add("injection_flagged", injection_flagged)
        _add("sandbox_passed", sandbox_passed)
        _add("overall_confidence", overall_confidence)
        _add("behavioral_score", behavioral_score)
        _add("started_at", started_at)
        _add("completed_at", completed_at)

        if not set_parts:
            return await self.get_eval_job(job_id)

        row = await self._conn.fetchrow(
            f"""
            UPDATE eval_jobs SET {", ".join(set_parts)}
            WHERE id = $1
            RETURNING {_EVAL_JOB_COLUMNS}
            """,  # noqa: S608
            *params,
        )
        if row is None:
            return None
        return _row_to_eval_job(row)

    async def get_latest_eval_for_skill(self, skill_id: uuid_mod.UUID) -> EvalJob | None:
        """Return the most recent eval job for a skill."""
        row = await self._conn.fetchrow(
            f"""
            SELECT {_EVAL_JOB_COLUMNS} FROM eval_jobs
            WHERE skill_id = $1
            ORDER BY created_at DESC
            LIMIT 1
            """,
            skill_id,
        )
        if row is None:
            return None
        return _row_to_eval_job(row)

    async def get_recent_completed_jobs(
        self, skill_id: uuid_mod.UUID, limit: int = 2
    ) -> list[EvalJob]:
        """Return the most recent completed eval jobs for a skill."""
        rows = await self._conn.fetch(
            f"""
            SELECT {_EVAL_JOB_COLUMNS} FROM eval_jobs
            WHERE skill_id = $1 AND status = 'completed'
            ORDER BY completed_at DESC
            LIMIT $2
            """,
            skill_id,
            limit,
        )
        return [_row_to_eval_job(row) for row in rows]

    async def get_recent_completed_jobs_all(self, limit: int = 40) -> list[EvalJob]:
        """Return the most recent completed eval jobs across all skills."""
        rows = await self._conn.fetch(
            f"""
            SELECT {_EVAL_JOB_COLUMNS} FROM eval_jobs
            WHERE status = 'completed'
            ORDER BY completed_at DESC
            LIMIT $1
            """,
            limit,
        )
        return [_row_to_eval_job(row) for row in rows]

    async def create_dimension_run(
        self,
        *,
        eval_job_id: uuid_mod.UUID,
        dimension: str,
        run_index: int,
        score: float,
        evidence: list[str],
        injection_detected: bool = False,
        injection_detail: str | None = None,
        confidence: float = 0.0,
        prompt_variant: str = "",
        model_id: str = "",
        latency_ms: int | None = None,
    ) -> EvalDimensionRun:
        """Insert a new dimension run and return it."""
        row = await self._conn.fetchrow(
            f"""
            INSERT INTO eval_dimension_runs (
                eval_job_id, dimension, run_index, score, evidence,
                injection_detected, injection_detail, confidence,
                prompt_variant, model_id, latency_ms
            ) VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7, $8, $9, $10, $11)
            RETURNING {_DIMENSION_RUN_COLUMNS}
            """,
            eval_job_id,
            dimension,
            run_index,
            score,
            json.dumps(evidence),
            injection_detected,
            injection_detail,
            confidence,
            prompt_variant,
            model_id,
            latency_ms,
        )
        return _row_to_dimension_run(row)

    async def get_runs_for_job(self, eval_job_id: uuid_mod.UUID) -> list[EvalDimensionRun]:
        """Return all dimension runs for an eval job, ordered by dimension and run_index."""
        rows = await self._conn.fetch(
            f"""
            SELECT {_DIMENSION_RUN_COLUMNS} FROM eval_dimension_runs
            WHERE eval_job_id = $1
            ORDER BY dimension, run_index
            """,
            eval_job_id,
        )
        return [_row_to_dimension_run(row) for row in rows]

    async def create_trust_audit_entry(
        self,
        *,
        skill_id: uuid_mod.UUID,
        previous_tier: str,
        new_tier: str,
        reason: str,
        eval_job_id: uuid_mod.UUID | None = None,
        promoted_by: uuid_mod.UUID | None = None,
    ) -> TrustAuditEntry:
        """Insert a trust tier change record and return it."""
        row = await self._conn.fetchrow(
            f"""
            INSERT INTO trust_audit_log (
                skill_id, previous_tier, new_tier, reason,
                eval_job_id, promoted_by
            ) VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING {_TRUST_AUDIT_COLUMNS}
            """,
            skill_id,
            previous_tier,
            new_tier,
            reason,
            eval_job_id,
            promoted_by,
        )
        return _row_to_trust_audit_entry(row)

    async def get_trust_history(self, skill_id: uuid_mod.UUID) -> list[TrustAuditEntry]:
        """Return trust tier change history for a skill, most recent first."""
        rows = await self._conn.fetch(
            f"""
            SELECT {_TRUST_AUDIT_COLUMNS} FROM trust_audit_log
            WHERE skill_id = $1
            ORDER BY created_at DESC
            """,
            skill_id,
        )
        return [_row_to_trust_audit_entry(row) for row in rows]
