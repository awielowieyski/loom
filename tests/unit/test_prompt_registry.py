"""Tests for the PromptRegistry — versioned prompt templates for LLM evaluation."""

import pytest

from loom.models.common import EvalDimension
from loom.services.prompt_registry import _BEHAVIORAL_REGISTRY, _REGISTRY, PromptRegistry


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


# ---------------------------------------------------------------------------
# Tests: Behavioral evaluation prompt variants
# ---------------------------------------------------------------------------


class TestBehavioralPromptRegistry:
    """Behavioral prompt registry behaviour."""

    def test_runner_role_has_variants(self, registry: PromptRegistry) -> None:
        """Runner role must have at least one variant."""
        variants = registry.list_behavioral_variants("runner")
        assert len(variants) >= 1

    def test_runner_has_two_variants(self, registry: PromptRegistry) -> None:
        """Runner should have exactly 2 variants."""
        assert len(registry.list_behavioral_variants("runner")) == 2

    def test_runner_prompt_contains_skill_runner(self, registry: PromptRegistry) -> None:
        """Runner prompt should contain 'SKILL RUNNER' or similar identifier."""
        variant = registry.get_behavioral_variant_by_name("runner", "runner-v1")
        assert "SKILL RUNNER" in variant.system_prompt

    def test_judge_role_has_variants(self, registry: PromptRegistry) -> None:
        """Judge role must have at least one variant."""
        variants = registry.list_behavioral_variants("judge")
        assert len(variants) >= 1

    def test_judge_has_two_variants(self, registry: PromptRegistry) -> None:
        """Judge should have exactly 2 variants."""
        assert len(registry.list_behavioral_variants("judge")) == 2

    def test_comparative_judge_role_has_variants(self, registry: PromptRegistry) -> None:
        """Comparative judge role must have at least one variant."""
        variants = registry.list_behavioral_variants("comparative_judge")
        assert len(variants) >= 1

    def test_get_behavioral_variant_by_name(self, registry: PromptRegistry) -> None:
        """get_behavioral_variant_by_name returns the exact variant."""
        variant = registry.get_behavioral_variant_by_name("judge", "judge-v1")
        assert variant.name == "judge-v1"

    def test_get_behavioral_variant_by_name_not_found(self, registry: PromptRegistry) -> None:
        """get_behavioral_variant_by_name raises KeyError for unknown names."""
        with pytest.raises(KeyError):
            registry.get_behavioral_variant_by_name("runner", "nonexistent")


class TestBehavioralSecurityInvariants:
    """All behavioral prompts must satisfy security requirements."""

    @pytest.mark.parametrize("role", ["runner", "judge", "comparative_judge"])
    def test_all_behavioral_prompts_contain_untrusted_warning(self, role: str) -> None:
        """Every behavioral system prompt MUST contain 'UNTRUSTED'."""
        for variant in _BEHAVIORAL_REGISTRY[role]:
            assert "UNTRUSTED" in variant.system_prompt, f"{variant.name} missing UNTRUSTED warning"

    @pytest.mark.parametrize("role", ["runner", "judge", "comparative_judge"])
    def test_all_behavioral_prompts_mention_injection(self, role: str) -> None:
        """Every behavioral system prompt MUST mention injection."""
        for variant in _BEHAVIORAL_REGISTRY[role]:
            prompt_lower = variant.system_prompt.lower()
            assert "injection" in prompt_lower, f"{variant.name} missing injection mention"

    @pytest.mark.parametrize("role", ["runner", "judge", "comparative_judge"])
    def test_no_format_markers_in_behavioral(self, role: str) -> None:
        """No behavioral prompt may contain '{' — no string interpolation."""
        for variant in _BEHAVIORAL_REGISTRY[role]:
            assert "{" not in variant.system_prompt, f"{variant.name} contains format marker"

    def test_judge_prompt_contains_output_judge(self, registry: PromptRegistry) -> None:
        """Judge prompt should identify itself as an output judge."""
        variant = registry.get_behavioral_variant_by_name("judge", "judge-v1")
        assert "SKILL OUTPUT JUDGE" in variant.system_prompt

    def test_comparative_judge_prompt_contains_comparative(self, registry: PromptRegistry) -> None:
        """Comparative judge prompt should identify as COMPARATIVE JUDGE."""
        variant = registry.get_behavioral_variant_by_name(
            "comparative_judge", "comparative-judge-v1"
        )
        assert "COMPARATIVE JUDGE" in variant.system_prompt

    @pytest.mark.parametrize("role", ["runner", "judge", "comparative_judge"])
    def test_behavioral_prompts_are_frozen(self, role: str) -> None:
        """PromptVariant is a frozen dataclass — immutable after creation."""
        for variant in _BEHAVIORAL_REGISTRY[role]:
            with pytest.raises(AttributeError):
                variant.name = "mutated"  # type: ignore[misc]
