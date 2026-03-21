"""Tests for EvalService structural validation."""

import pytest

from loom.models.common import EvalScenario, EvalSpec
from loom.models.skill import SkillCreate
from loom.services.eval import EvalService


@pytest.fixture
def service() -> EvalService:
    return EvalService()


def _make_valid_skill(**overrides: object) -> SkillCreate:
    defaults: dict[str, object] = {
        "slug": "test-skill",
        "name": "Test Skill",
        "description": "A test skill",
        "content": "This is valid content for the skill that is long enough",
        "category_slug": "test-category",
        "version": "1.0.0",
        "eval_spec": EvalSpec(
            scenarios=[EvalScenario(description="d", input_context="c", success_criteria="s")]
        ),
    }
    defaults.update(overrides)
    return SkillCreate(**defaults)  # type: ignore[arg-type]


def test_valid_skill_passes(service: EvalService) -> None:
    skill = _make_valid_skill()
    result = service.validate_structure(skill)
    assert result.passed is True
    assert result.errors == []


def test_empty_content_fails(service: EvalService) -> None:
    skill = _make_valid_skill(content="")
    result = service.validate_structure(skill)
    assert result.passed is False
    assert any("content" in e.lower() for e in result.errors)


def test_short_content_fails(service: EvalService) -> None:
    skill = _make_valid_skill(content="short")
    result = service.validate_structure(skill)
    assert result.passed is False
    assert any("content" in e.lower() for e in result.errors)


def test_missing_scenarios_fails(service: EvalService) -> None:
    skill = _make_valid_skill(eval_spec=EvalSpec(scenarios=[]))
    result = service.validate_structure(skill)
    assert result.passed is False
    assert any("scenario" in e.lower() for e in result.errors)
