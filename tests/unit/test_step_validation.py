"""Tests for step reference validation in CapabilityRegistryService."""

import pytest

from loom.models.capability import CapabilityStep
from loom.services.capability_registry import CapabilityRegistryService


def _make_step(skill_ref: str, role: str = "test role") -> CapabilityStep:
    return CapabilityStep(skill_ref=skill_ref, role=role)


class TestValidateSteps:
    """Tests for _validate_steps static method."""

    def test_loom_uri_passes(self) -> None:
        steps = [_make_step("loom://my-skill")]
        warnings = CapabilityRegistryService._validate_steps(steps)
        assert warnings == []

    def test_corp_uri_passes_with_warning(self) -> None:
        steps = [_make_step("corp://internal-skill")]
        warnings = CapabilityRegistryService._validate_steps(steps)
        assert len(warnings) == 1
        assert "corp://internal-skill" in warnings[0]
        assert "not resolvable in a public context" in warnings[0]

    def test_bare_slug_fails_at_model_level(self) -> None:
        """A bare slug without URI prefix is rejected by the Pydantic model validator."""
        with pytest.raises(ValueError, match="URI scheme prefix"):
            _make_step("bare-slug")

    def test_empty_skill_ref_fails_at_model_level(self) -> None:
        """An empty skill_ref is rejected by the Pydantic model validator."""
        with pytest.raises(ValueError, match="URI scheme prefix"):
            _make_step("")

    def test_empty_slug_after_scheme_fails(self) -> None:
        """A URI with valid scheme but empty slug is rejected."""
        steps = [_make_step("loom://")]
        with pytest.raises(ValueError, match="empty slug"):
            CapabilityRegistryService._validate_steps(steps)

    def test_multiple_valid_steps(self) -> None:
        steps = [
            _make_step("loom://skill-a"),
            _make_step("loom://skill-b"),
            _make_step("loom://skill-c"),
        ]
        warnings = CapabilityRegistryService._validate_steps(steps)
        assert warnings == []

    def test_mixed_schemes_collect_warnings(self) -> None:
        steps = [
            _make_step("loom://skill-a"),
            _make_step("corp://skill-b"),
            _make_step("loom://skill-c"),
            _make_step("corp://skill-d"),
        ]
        warnings = CapabilityRegistryService._validate_steps(steps)
        assert len(warnings) == 2
        assert all("corp://" in w for w in warnings)

    def test_custom_scheme_passes(self) -> None:
        """Non-standard schemes (e.g. custom://) pass structural validation.

        The step validator only enforces the presence of ://, not specific schemes.
        Scheme validation is handled at resolution time.
        """
        steps = [_make_step("custom://my-thing")]
        warnings = CapabilityRegistryService._validate_steps(steps)
        assert warnings == []

    def test_step_index_in_warning(self) -> None:
        """Warning messages include the step index for debugging."""
        steps = [
            _make_step("loom://skill-a"),
            _make_step("corp://internal"),
        ]
        warnings = CapabilityRegistryService._validate_steps(steps)
        assert len(warnings) == 1
        assert "Step 1" in warnings[0]
