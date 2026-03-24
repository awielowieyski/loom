"""TrustService: automated trust-tier promotion logic."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from loom.models.common import TrustTier

if TYPE_CHECKING:
    import uuid as uuid_mod


class PromotionDecision(BaseModel):
    should_promote: bool
    target_tier: TrustTier | None = None
    reason: str


class TrustService:
    """Evaluates whether a skill qualifies for trust-tier promotion."""

    def __init__(
        self,
        eval_repo: Any,
        *,
        promotion_threshold: float = 0.70,
        safety_floor: float = 0.60,
        min_usage_count: int = 10,
        min_success_rate: float = 0.80,
        behavioral_floor: float = 0.60,
    ) -> None:
        self._eval_repo = eval_repo
        self._promotion_threshold = promotion_threshold
        self._safety_floor = safety_floor
        self._min_usage_count = min_usage_count
        self._min_success_rate = min_success_rate
        self._behavioral_floor = behavioral_floor

    async def check_promotion(
        self,
        skill_id: uuid_mod.UUID,
        current_tier: TrustTier,
        is_signed: bool,
        usage_count: int,
        success_rate: float,
        behavioral_score: float | None = None,
    ) -> PromotionDecision:
        """Decide whether *skill_id* should be promoted from *current_tier*."""

        # Only auto-promote experimental -> community
        if current_tier != TrustTier.EXPERIMENTAL:
            return PromotionDecision(
                should_promote=False,
                reason="requires manual promotion by steward",
            )

        # Check signing
        if not is_signed:
            return PromotionDecision(
                should_promote=False,
                reason="skill must be signed before promotion",
            )

        # Check usage count
        if usage_count < self._min_usage_count:
            return PromotionDecision(
                should_promote=False,
                reason=(f"insufficient usage count ({usage_count} < {self._min_usage_count})"),
            )

        # Check success rate
        if success_rate < self._min_success_rate:
            return PromotionDecision(
                should_promote=False,
                reason=(f"low success rate ({success_rate:.2f} < {self._min_success_rate:.2f})"),
            )

        # Check behavioral score (M4)
        if behavioral_score is not None and behavioral_score < self._behavioral_floor:
            return PromotionDecision(
                should_promote=False,
                reason=(
                    f"behavioral score below floor "
                    f"({behavioral_score:.2f} < {self._behavioral_floor:.2f})"
                ),
            )

        # Fetch latest eval
        latest_eval = await self._eval_repo.get_latest_eval_for_skill(skill_id)
        if latest_eval is None:
            return PromotionDecision(
                should_promote=False,
                reason="no evaluation found for skill",
            )

        # Check injection flags
        if latest_eval.injection_flagged:
            return PromotionDecision(
                should_promote=False,
                reason="latest evaluation flagged for injection",
            )

        # Check composite score
        composite = latest_eval.composite_score or 0.0
        if composite < self._promotion_threshold:
            return PromotionDecision(
                should_promote=False,
                reason=(
                    f"composite score too low ({composite:.2f} < {self._promotion_threshold:.2f})"
                ),
            )

        # Check safety dimension score
        dimension_scores = latest_eval.dimension_scores or {}
        safety_score = dimension_scores.get("safety", 0.0)
        if safety_score < self._safety_floor:
            return PromotionDecision(
                should_promote=False,
                reason=(
                    f"safety score below floor ({safety_score:.2f} < {self._safety_floor:.2f})"
                ),
            )

        return PromotionDecision(
            should_promote=True,
            target_tier=TrustTier.COMMUNITY,
            reason="all promotion criteria met",
        )
