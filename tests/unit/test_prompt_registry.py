"""Tests for the PromptRegistry — versioned prompt templates for LLM evaluation."""

import pytest

from loom.models.common import EvalDimension
from loom.services.prompt_registry import _REGISTRY, PromptRegistry


@pytest.fixture
def registry() -> PromptRegistry:
    return PromptRegistry()


class TestPromptRegistry:
    """Core registry behaviour."""

    def test_all_dimensions_have_variants(self, registry: PromptRegistry) -> None:
        """Every EvalDimension must have at least one variant."""
        for dim in EvalDimension:
            variants = registry.list_variants(dim)
            assert len(variants) >= 1, f"{dim.value} has no variants"

    def test_clarity_has_two_variants(self, registry: PromptRegistry) -> None:
        """Clarity should have exactly 2 variants per the plan."""
        assert len(registry.list_variants(EvalDimension.CLARITY)) == 2

    def test_get_variant_returns_valid_prompt(self, registry: PromptRegistry) -> None:
        """get_variant returns a PromptVariant with non-empty fields."""
        variant = registry.get_variant(EvalDimension.CLARITY)
        assert variant.name
        assert variant.system_prompt

    def test_get_variant_by_name(self, registry: PromptRegistry) -> None:
        """get_variant_by_name returns the exact variant requested."""
        variant = registry.get_variant_by_name(EvalDimension.CLARITY, "clarity-v1")
        assert variant.name == "clarity-v1"

    def test_get_variant_by_name_not_found(self, registry: PromptRegistry) -> None:
        """get_variant_by_name raises KeyError for unknown names."""
        with pytest.raises(KeyError):
            registry.get_variant_by_name(EvalDimension.CLARITY, "nonexistent")


class TestSecurityInvariants:
    """All prompts must satisfy security requirements."""

    @pytest.mark.parametrize("dimension", list(EvalDimension))
    def test_all_prompts_contain_untrusted_warning(self, dimension: EvalDimension) -> None:
        """Every system prompt MUST contain the word 'UNTRUSTED'."""
        for variant in _REGISTRY[dimension]:
            assert "UNTRUSTED" in variant.system_prompt, f"{variant.name} missing UNTRUSTED warning"

    @pytest.mark.parametrize("dimension", list(EvalDimension))
    def test_all_prompts_mention_injection_detection(self, dimension: EvalDimension) -> None:
        """Every system prompt MUST mention injection detection."""
        for variant in _REGISTRY[dimension]:
            prompt_lower = variant.system_prompt.lower()
            assert (
                "injection" in prompt_lower
            ), f"{variant.name} missing injection detection mention"

    @pytest.mark.parametrize("dimension", list(EvalDimension))
    def test_no_format_markers(self, dimension: EvalDimension) -> None:
        """No system prompt may contain '{' — no string interpolation allowed."""
        for variant in _REGISTRY[dimension]:
            assert "{" not in variant.system_prompt, f"{variant.name} contains '{{' format marker"

    @pytest.mark.parametrize("dimension", list(EvalDimension))
    def test_prompts_are_frozen(self, dimension: EvalDimension) -> None:
        """PromptVariant is a frozen dataclass — immutable after creation."""
        for variant in _REGISTRY[dimension]:
            with pytest.raises(AttributeError):
                variant.name = "mutated"  # type: ignore[misc]
