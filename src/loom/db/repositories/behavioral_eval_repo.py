"""Behavioral and comparative evaluation repository with raw asyncpg SQL."""

import uuid as uuid_mod
from typing import Any

import asyncpg

from loom.models.behavioral import BehavioralRunResult, ComparativeResult, SkillRanking

_BEHAVIORAL_RUN_COLUMNS = (
    "id, eval_job_id, scenario_index, run_index, runner_output, "
    "judge_score, judge_evidence, judge_confidence, injection_detected, "
    "runner_model_id, judge_model_id, runner_latency_ms, judge_latency_ms, created_at"
)

_COMPARATIVE_RESULT_COLUMNS = (
    "id, skill_a_id, skill_a_version, skill_b_id, skill_b_version, "
    "scenario_index, winner, score_a, score_b, preference_confidence, "
    "reasoning, classification, judge_model_id, created_at"
)

_SKILL_RANKING_COLUMNS = (
    "id, skill_id, category_id, rating, matches_played, "
    "wins, losses, ties, last_match_at, updated_at"
)


def _row_to_behavioral_run(row: asyncpg.Record) -> BehavioralRunResult:
    return BehavioralRunResult(**dict(row))


def _row_to_comparative_result(row: asyncpg.Record) -> ComparativeResult:
    return ComparativeResult(**dict(row))


def _row_to_skill_ranking(row: asyncpg.Record) -> SkillRanking:
    return SkillRanking(**dict(row))


class BehavioralEvalRepo:
    """Repository for behavioral evaluation and comparative result persistence."""

    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    async def create_behavioral_run(
        self,
        *,
        eval_job_id: uuid_mod.UUID,
        scenario_index: int,
        run_index: int,
        runner_output: dict[str, Any],
        judge_score: float,
        judge_evidence: dict[str, Any],
        judge_confidence: float,
        injection_detected: bool = False,
        runner_model_id: str,
        judge_model_id: str,
        runner_latency_ms: int | None = None,
        judge_latency_ms: int | None = None,
    ) -> BehavioralRunResult:
        """Insert a behavioral evaluation run and return it."""
        row = await self._conn.fetchrow(
            f"""
            INSERT INTO behavioral_eval_runs (
                eval_job_id, scenario_index, run_index, runner_output,
                judge_score, judge_evidence, judge_confidence,
                injection_detected, runner_model_id, judge_model_id,
                runner_latency_ms, judge_latency_ms
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            RETURNING {_BEHAVIORAL_RUN_COLUMNS}
            """,
            eval_job_id,
            scenario_index,
            run_index,
            runner_output,
            judge_score,
            judge_evidence,
            judge_confidence,
            injection_detected,
            runner_model_id,
            judge_model_id,
            runner_latency_ms,
            judge_latency_ms,
        )
        return _row_to_behavioral_run(row)

    async def get_runs_for_job(
        self,
        eval_job_id: uuid_mod.UUID,
    ) -> list[BehavioralRunResult]:
        """Return all behavioral runs for an eval job, ordered by scenario and run index."""
        rows = await self._conn.fetch(
            f"""
            SELECT {_BEHAVIORAL_RUN_COLUMNS} FROM behavioral_eval_runs
            WHERE eval_job_id = $1
            ORDER BY scenario_index, run_index
            """,
            eval_job_id,
        )
        return [_row_to_behavioral_run(row) for row in rows]

    async def get_latest_behavioral_for_skill(
        self,
        skill_id: uuid_mod.UUID,
    ) -> list[BehavioralRunResult] | None:
        """Return behavioral runs for the latest eval job of a skill."""
        rows = await self._conn.fetch(
            f"""
            SELECT br.{_BEHAVIORAL_RUN_COLUMNS.replace(", ", ", br.")}
            FROM behavioral_eval_runs br
            JOIN eval_jobs ej ON br.eval_job_id = ej.id
            WHERE ej.skill_id = $1
            ORDER BY ej.created_at DESC, br.scenario_index, br.run_index
            """,
            skill_id,
        )
        if not rows:
            return None
        # Filter to only the latest job
        latest_job_id = rows[0]["eval_job_id"]
        return [_row_to_behavioral_run(row) for row in rows if row["eval_job_id"] == latest_job_id]

    async def create_comparative_result(
        self,
        *,
        skill_a_id: uuid_mod.UUID,
        skill_a_version: str,
        skill_b_id: uuid_mod.UUID,
        skill_b_version: str,
        scenario_index: int,
        winner: str,
        score_a: dict[str, Any],
        score_b: dict[str, Any],
        preference_confidence: float,
        reasoning: str,
        classification: str | None = None,
        judge_model_id: str,
    ) -> ComparativeResult:
        """Insert a comparative evaluation result and return it."""
        row = await self._conn.fetchrow(
            f"""
            INSERT INTO comparative_eval_results (
                skill_a_id, skill_a_version, skill_b_id, skill_b_version,
                scenario_index, winner, score_a, score_b,
                preference_confidence, reasoning, classification, judge_model_id
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            RETURNING {_COMPARATIVE_RESULT_COLUMNS}
            """,
            skill_a_id,
            skill_a_version,
            skill_b_id,
            skill_b_version,
            scenario_index,
            winner,
            score_a,
            score_b,
            preference_confidence,
            reasoning,
            classification,
            judge_model_id,
        )
        return _row_to_comparative_result(row)

    async def get_comparisons_for_skill(
        self,
        skill_id: uuid_mod.UUID,
    ) -> list[ComparativeResult]:
        """Return all comparative results involving a skill (as either a or b)."""
        rows = await self._conn.fetch(
            f"""
            SELECT {_COMPARATIVE_RESULT_COLUMNS} FROM comparative_eval_results
            WHERE skill_a_id = $1 OR skill_b_id = $1
            ORDER BY created_at DESC
            """,
            skill_id,
        )
        return [_row_to_comparative_result(row) for row in rows]

    async def upsert_ranking(
        self,
        *,
        skill_id: uuid_mod.UUID,
        category_id: uuid_mod.UUID,
        rating: float,
        matches_played: int,
        wins: int,
        losses: int,
        ties: int,
    ) -> SkillRanking:
        """Insert or update a skill ranking for a category."""
        row = await self._conn.fetchrow(
            f"""
            INSERT INTO skill_rankings (
                skill_id, category_id, rating, matches_played,
                wins, losses, ties, last_match_at, updated_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, now(), now())
            ON CONFLICT (skill_id, category_id) DO UPDATE SET
                rating = EXCLUDED.rating,
                matches_played = EXCLUDED.matches_played,
                wins = EXCLUDED.wins,
                losses = EXCLUDED.losses,
                ties = EXCLUDED.ties,
                last_match_at = now(),
                updated_at = now()
            RETURNING {_SKILL_RANKING_COLUMNS}
            """,
            skill_id,
            category_id,
            rating,
            matches_played,
            wins,
            losses,
            ties,
        )
        return _row_to_skill_ranking(row)

    async def get_ranking(
        self,
        skill_id: uuid_mod.UUID,
        category_id: uuid_mod.UUID,
    ) -> SkillRanking | None:
        """Return a skill's ranking for a category."""
        row = await self._conn.fetchrow(
            f"""
            SELECT {_SKILL_RANKING_COLUMNS} FROM skill_rankings
            WHERE skill_id = $1 AND category_id = $2
            """,
            skill_id,
            category_id,
        )
        if row is None:
            return None
        return _row_to_skill_ranking(row)
