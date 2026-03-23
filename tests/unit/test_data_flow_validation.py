"""Tests for data flow validation in CapabilityRegistryService."""

from loom.models.capability import CapabilityStep, DataFlowEdge
from loom.services.capability_registry import CapabilityRegistryService


def _make_step(slug: str, role: str = "test role") -> CapabilityStep:
    return CapabilityStep(skill_ref=f"loom://{slug}", role=role)


def _steps_abc() -> list[CapabilityStep]:
    """Three steps: loom://a (idx 0), loom://b (idx 1), loom://c (idx 2)."""
    return [
        _make_step("a", "Step A"),
        _make_step("b", "Step B"),
        _make_step("c", "Step C"),
    ]


class TestValidateDataFlow:
    """Tests for _validate_data_flow static method."""

    def test_valid_forward_flow(self) -> None:
        """Step 0 output consumed by step 2 input passes."""
        steps = _steps_abc()
        data_flow = [DataFlowEdge(from_step="a", to_step="c", classification="internal")]

        errors = CapabilityRegistryService._validate_data_flow(steps, data_flow)
        assert errors == []

    def test_valid_adjacent_flow(self) -> None:
        """Step 0 -> step 1 is valid forward flow."""
        steps = _steps_abc()
        data_flow = [DataFlowEdge(from_step="a", to_step="b", classification="internal")]

        errors = CapabilityRegistryService._validate_data_flow(steps, data_flow)
        assert errors == []

    def test_nonexistent_from_step_fails(self) -> None:
        """Reference to a non-existent from_step slug fails."""
        steps = _steps_abc()
        data_flow = [DataFlowEdge(from_step="missing", to_step="b", classification="internal")]

        errors = CapabilityRegistryService._validate_data_flow(steps, data_flow)
        assert len(errors) == 1
        assert "from_step" in errors[0]
        assert "'missing'" in errors[0]

    def test_nonexistent_to_step_fails(self) -> None:
        """Reference to a non-existent to_step slug fails."""
        steps = _steps_abc()
        data_flow = [DataFlowEdge(from_step="a", to_step="missing", classification="internal")]

        errors = CapabilityRegistryService._validate_data_flow(steps, data_flow)
        assert len(errors) == 1
        assert "to_step" in errors[0]
        assert "'missing'" in errors[0]

    def test_backward_flow_fails(self) -> None:
        """Step 2 output consumed by step 0 input (backward) fails."""
        steps = _steps_abc()
        data_flow = [DataFlowEdge(from_step="c", to_step="a", classification="internal")]

        errors = CapabilityRegistryService._validate_data_flow(steps, data_flow)
        assert len(errors) == 1
        assert "backward or self-referencing" in errors[0]

    def test_self_referencing_flow_fails(self) -> None:
        """Same step as both from and to fails."""
        steps = _steps_abc()
        data_flow = [DataFlowEdge(from_step="b", to_step="b", classification="internal")]

        errors = CapabilityRegistryService._validate_data_flow(steps, data_flow)
        assert len(errors) == 1
        assert "backward or self-referencing" in errors[0]

    def test_invalid_classification_fails(self) -> None:
        """Classification must be one of internal, external, confidential."""
        steps = _steps_abc()
        data_flow = [DataFlowEdge(from_step="a", to_step="b", classification="secret")]

        errors = CapabilityRegistryService._validate_data_flow(steps, data_flow)
        assert len(errors) == 1
        assert "invalid classification" in errors[0]
        assert "'secret'" in errors[0]

    def test_valid_classifications(self) -> None:
        """All valid classification values pass."""
        steps = _steps_abc()
        data_flow = [
            DataFlowEdge(from_step="a", to_step="b", classification="internal"),
            DataFlowEdge(from_step="a", to_step="c", classification="external"),
            DataFlowEdge(from_step="b", to_step="c", classification="confidential"),
        ]

        errors = CapabilityRegistryService._validate_data_flow(steps, data_flow)
        assert errors == []

    def test_empty_data_flow_passes(self) -> None:
        """No data flow edges is always valid."""
        steps = _steps_abc()
        errors = CapabilityRegistryService._validate_data_flow(steps, [])
        assert errors == []

    def test_multiple_errors_reported(self) -> None:
        """Multiple issues are all reported at once."""
        steps = _steps_abc()
        data_flow = [
            DataFlowEdge(from_step="missing", to_step="also-missing", classification="invalid"),
        ]

        errors = CapabilityRegistryService._validate_data_flow(steps, data_flow)
        # Should have errors for: from_step unknown, to_step unknown, invalid classification
        assert len(errors) == 3

    def test_edge_index_in_error_messages(self) -> None:
        """Error messages include the edge index for debugging."""
        steps = _steps_abc()
        data_flow = [
            DataFlowEdge(from_step="a", to_step="b", classification="internal"),
            DataFlowEdge(from_step="c", to_step="a", classification="internal"),
        ]

        errors = CapabilityRegistryService._validate_data_flow(steps, data_flow)
        assert len(errors) == 1
        assert "edge 1" in errors[0]
