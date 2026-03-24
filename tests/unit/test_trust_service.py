"""Tests for TrustService: automated trust-tier promotion logic."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from loom.models.common import TrustTier
from loom.services.trust_service import TrustService


def _make_eval(
    *,
    composite_score: float = 0.85,
    dimension_scores: dict[str, float] | None = None,
    injection_flagged: bool = False,
) -> MagicMock:
    """Create a mock eval job with sensible defaults."""
    eval_obj = MagicMock()
    eval_obj.composite_score = composite_score
    eval_obj.dimension_scores = dimension_scores or {"safety": 0.90, "clarity": 0.80}
    eval_obj.injection_flagged = injection_flagged
    return eval_obj


def _make_service(eval_obj: object | None = None) -> TrustService:
    """Build a TrustService with mocked repos."""
    eval_repo = AsyncMock()
    eval_repo.get_latest_eval_for_skill.return_value = eval_obj
    return TrustService(eval_repo=eval_repo)


SKILL_ID = uuid.uuid4()


class TestCheckPromotion:
    @pytest.mark.asyncio
    async def test_all_criteria_met(self) -> None:
        svc = _make_service(_make_eval())
        decision = await svc.check_promotion(
            skill_id=SKILL_ID,
            current_tier=TrustTier.EXPERIMENTAL,
            is_signed=True,
            usage_count=20,
            success_rate=0.95,
        )
        assert decision.should_promote is True
        assert decision.target_tier == TrustTier.COMMUNITY

    @pytest.mark.asyncio
    async def test_low_score_no_promotion(self) -> None:
        svc = _make_service(_make_eval(composite_score=0.50))
        decision = await svc.check_promotion(
            skill_id=SKILL_ID,
            current_tier=TrustTier.EXPERIMENTAL,
            is_signed=True,
            usage_count=20,
            success_rate=0.95,
        )
        assert decision.should_promote is False
        assert "score" in decision.reason.lower()

    @pytest.mark.asyncio
    async def test_unsigned_no_promotion(self) -> None:
        svc = _make_service(_make_eval())
        decision = await svc.check_promotion(
            skill_id=SKILL_ID,
            current_tier=TrustTier.EXPERIMENTAL,
            is_signed=False,
            usage_count=20,
            success_rate=0.95,
        )
        assert decision.should_promote is False
        assert "sign" in decision.reason.lower()

    @pytest.mark.asyncio
    async def test_injection_flagged_no_promotion(self) -> None:
        svc = _make_service(_make_eval(injection_flagged=True))
        decision = await svc.check_promotion(
            skill_id=SKILL_ID,
            current_tier=TrustTier.EXPERIMENTAL,
            is_signed=True,
            usage_count=20,
            success_rate=0.95,
        )
        assert decision.should_promote is False
        assert "injection" in decision.reason.lower()

    @pytest.mark.asyncio
    async def test_community_no_auto_promotion(self) -> None:
        svc = _make_service(_make_eval())
        decision = await svc.check_promotion(
            skill_id=SKILL_ID,
            current_tier=TrustTier.COMMUNITY,
            is_signed=True,
            usage_count=20,
            success_rate=0.95,
        )
        assert decision.should_promote is False
        assert "manual" in decision.reason.lower()

    @pytest.mark.asyncio
    async def test_insufficient_usage_no_promotion(self) -> None:
        svc = _make_service(_make_eval())
        decision = await svc.check_promotion(
            skill_id=SKILL_ID,
            current_tier=TrustTier.EXPERIMENTAL,
            is_signed=True,
            usage_count=5,
            success_rate=0.95,
        )
        assert decision.should_promote is False
        assert "usage" in decision.reason.lower()

    @pytest.mark.asyncio
    async def test_low_success_rate_no_promotion(self) -> None:
        svc = _make_service(_make_eval())
        decision = await svc.check_promotion(
            skill_id=SKILL_ID,
            current_tier=TrustTier.EXPERIMENTAL,
            is_signed=True,
            usage_count=20,
            success_rate=0.50,
        )
        assert decision.should_promote is False
        assert "success rate" in decision.reason.lower()

    @pytest.mark.asyncio
    async def test_safety_below_floor_no_promotion(self) -> None:
        svc = _make_service(_make_eval(dimension_scores={"safety": 0.40, "clarity": 0.80}))
        decision = await svc.check_promotion(
            skill_id=SKILL_ID,
            current_tier=TrustTier.EXPERIMENTAL,
            is_signed=True,
            usage_count=20,
            success_rate=0.95,
        )
        assert decision.should_promote is False
        assert "safety" in decision.reason.lower()

    @pytest.mark.asyncio
    async def test_behavioral_score_below_floor_blocks_promotion(self) -> None:
        svc = _make_service(_make_eval())
        decision = await svc.check_promotion(
            skill_id=SKILL_ID,
            current_tier=TrustTier.EXPERIMENTAL,
            is_signed=True,
            usage_count=20,
            success_rate=0.95,
            behavioral_score=0.40,
        )
        assert decision.should_promote is False
        assert "behavioral" in decision.reason.lower()

    @pytest.mark.asyncio
    async def test_behavioral_score_none_does_not_block(self) -> None:
        """When behavioral_score is None (not yet evaluated), skip the check."""
        svc = _make_service(_make_eval())
        decision = await svc.check_promotion(
            skill_id=SKILL_ID,
            current_tier=TrustTier.EXPERIMENTAL,
            is_signed=True,
            usage_count=20,
            success_rate=0.95,
            behavioral_score=None,
        )
        assert decision.should_promote is True

    @pytest.mark.asyncio
    async def test_behavioral_score_above_floor_passes(self) -> None:
        svc = _make_service(_make_eval())
        decision = await svc.check_promotion(
            skill_id=SKILL_ID,
            current_tier=TrustTier.EXPERIMENTAL,
            is_signed=True,
            usage_count=20,
            success_rate=0.95,
            behavioral_score=0.80,
        )
        assert decision.should_promote is True
