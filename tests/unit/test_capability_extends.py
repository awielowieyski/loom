"""Unit tests for capability extends support in ExtendsResolver."""

from __future__ import annotations

import pytest

from loom.extends.resolver import (
    ExtendsResolver,
    ResolvedCapabilityChain,
    validate_step_sources,
)


@pytest.fixture
def resolver() -> ExtendsResolver:
    return ExtendsResolver()


# ======================================================================
# Task 11: merge_capability_layers — basic merge behaviour
# ======================================================================


class TestMergeCapabilityLayers:
    """Append-only capability layer merging."""

    def test_single_layer_returns_steps_unchanged(self, resolver: ExtendsResolver) -> None:
        layers = [
            {
                "source": "loom",
                "slug": "base-cap",
                "version": "1.0.0",
                "steps": [
                    {"skill_ref": "loom://review-pr", "role": "Review PR"},
                    {"skill_ref": "loom://review-security", "role": "Security review"},
                ],
                "preconditions": ["Diff available"],
                "expected_outcome": "Combined review",
                "data_flow": [
                    {
                        "from_step": "review-pr",
                        "to_step": "review-security",
                        "classification": "internal",
                    }
                ],
            }
        ]
        result = resolver.merge_capability_layers(layers)
        assert isinstance(result, ResolvedCapabilityChain)
        assert len(result.steps) == 2
        assert result.steps[0]["skill_ref"] == "loom://review-pr"
        assert result.steps[1]["skill_ref"] == "loom://review-security"
        assert result.preconditions == ["Diff available"]
        assert result.expected_outcome == "Combined review"
        assert len(result.data_flow) == 1
        assert len(result.layers) == 1

    def test_two_layers_appends_steps(self, resolver: ExtendsResolver) -> None:
        """Capability B extends A: result has A's steps then B's steps."""
        layers = [
            {
                "slug": "cap-a",
                "steps": [
                    {"skill_ref": "loom://step-a1", "role": "Role A1"},
                    {"skill_ref": "loom://step-a2", "role": "Role A2"},
                ],
                "preconditions": ["Pre A"],
                "expected_outcome": "Outcome A",
            },
            {
                "slug": "cap-b",
                "steps": [
                    {"skill_ref": "loom://step-b1", "role": "Role B1"},
                ],
                "preconditions": ["Pre B"],
                "expected_outcome": "Outcome B",
            },
        ]
        result = resolver.merge_capability_layers(layers)
        assert len(result.steps) == 3
        assert result.steps[0]["role"] == "Role A1"
        assert result.steps[1]["role"] == "Role A2"
        assert result.steps[2]["role"] == "Role B1"

    def test_preconditions_merged(self, resolver: ExtendsResolver) -> None:
        layers = [
            {"slug": "a", "steps": [], "preconditions": ["P1", "P2"]},
            {"slug": "b", "steps": [], "preconditions": ["P3"]},
        ]
        result = resolver.merge_capability_layers(layers)
        assert result.preconditions == ["P1", "P2", "P3"]

    def test_expected_outcome_uses_last_nonempty(self, resolver: ExtendsResolver) -> None:
        layers = [
            {"slug": "a", "steps": [], "expected_outcome": "Outcome A"},
            {"slug": "b", "steps": [], "expected_outcome": "Outcome B"},
        ]
        result = resolver.merge_capability_layers(layers)
        assert result.expected_outcome == "Outcome B"

    def test_expected_outcome_falls_back_to_base(self, resolver: ExtendsResolver) -> None:
        layers = [
            {"slug": "a", "steps": [], "expected_outcome": "Outcome A"},
            {"slug": "b", "steps": [], "expected_outcome": ""},
        ]
        result = resolver.merge_capability_layers(layers)
        assert result.expected_outcome == "Outcome A"

    def test_data_flow_edges_merged(self, resolver: ExtendsResolver) -> None:
        layers = [
            {
                "slug": "a",
                "steps": [{"skill_ref": "loom://s1", "role": "R1"}],
                "data_flow": [{"from_step": "s1", "to_step": "s2", "classification": "internal"}],
            },
            {
                "slug": "b",
                "steps": [{"skill_ref": "loom://s3", "role": "R3"}],
                "data_flow": [{"from_step": "s2", "to_step": "s3", "classification": "external"}],
            },
        ]
        result = resolver.merge_capability_layers(layers)
        assert len(result.data_flow) == 2
        assert result.data_flow[0]["classification"] == "internal"
        assert result.data_flow[1]["classification"] == "external"

    def test_base_step_fields_preserved(self, resolver: ExtendsResolver) -> None:
        """A's step fields are preserved exactly in the merged result."""
        step_a = {
            "skill_ref": "loom://code-review",
            "role": "Review code",
            "inputs": {"diff": "$input.diff"},
            "outputs": {"review": "$result"},
            "required": True,
            "data_classification": "internal",
        }
        layers = [
            {"slug": "a", "steps": [step_a]},
            {
                "slug": "b",
                "steps": [{"skill_ref": "loom://perf-review", "role": "Perf review"}],
            },
        ]
        result = resolver.merge_capability_layers(layers)
        assert result.steps[0] == step_a

    def test_empty_layers_returns_empty(self, resolver: ExtendsResolver) -> None:
        result = resolver.merge_capability_layers([])
        assert result.steps == []
        assert result.preconditions == []
        assert result.expected_outcome == ""

    def test_layer_info_populated(self, resolver: ExtendsResolver) -> None:
        layers = [
            {
                "source": "loom",
                "slug": "base",
                "version": "1.0.0",
                "steps": [{"skill_ref": "loom://s1", "role": "R1"}],
            },
            {
                "source": "corp",
                "slug": "overlay",
                "version": "2.0.0",
                "steps": [{"skill_ref": "corp://s2", "role": "R2"}],
            },
        ]
        result = resolver.merge_capability_layers(layers)
        assert len(result.layers) == 2
        assert result.layers[0].source == "loom"
        assert result.layers[0].slug == "base"
        assert result.layers[1].source == "corp"
        assert result.layers[1].slug == "overlay"


# ======================================================================
# Task 13: Cycle detection
# ======================================================================


class TestResolveExtendsChain:
    """Extends chain resolution with cycle and depth detection."""

    def test_no_cycle_chain(self, resolver: ExtendsResolver) -> None:
        """A -> B -> C (no cycle) resolves successfully."""
        lookup = {
            "loom://c": {"slug": "c", "steps": [{"skill_ref": "loom://s1", "role": "R1"}]},
            "loom://b": {
                "slug": "b",
                "extends": "loom://c",
                "steps": [{"skill_ref": "loom://s2", "role": "R2"}],
            },
            "loom://a": {
                "slug": "a",
                "extends": "loom://b",
                "steps": [{"skill_ref": "loom://s3", "role": "R3"}],
            },
        }
        chain = resolver.resolve_extends_chain("loom://a", lookup)
        assert len(chain) == 3
        # Bottom-up: C first, then B, then A
        assert chain[0]["slug"] == "c"
        assert chain[1]["slug"] == "b"
        assert chain[2]["slug"] == "a"

    def test_direct_cycle_raises(self, resolver: ExtendsResolver) -> None:
        """A extends B, B extends A → cycle error."""
        lookup = {
            "loom://a": {
                "slug": "a",
                "extends": "loom://b",
                "steps": [],
            },
            "loom://b": {
                "slug": "b",
                "extends": "loom://a",
                "steps": [],
            },
        }
        with pytest.raises(ValueError, match="Circular extends chain detected"):
            resolver.resolve_extends_chain("loom://a", lookup)

    def test_transitive_cycle_raises(self, resolver: ExtendsResolver) -> None:
        """A -> B -> C -> A → cycle error listing full chain."""
        lookup = {
            "loom://a": {"slug": "a", "extends": "loom://b", "steps": []},
            "loom://b": {"slug": "b", "extends": "loom://c", "steps": []},
            "loom://c": {"slug": "c", "extends": "loom://a", "steps": []},
        }
        with pytest.raises(ValueError, match="Circular extends chain detected"):
            resolver.resolve_extends_chain("loom://a", lookup)

    def test_depth_limit_at_max(self, resolver: ExtendsResolver) -> None:
        """Chain of exactly MAX_EXTENDS_DEPTH succeeds."""
        from loom.extends.resolver import MAX_EXTENDS_DEPTH

        lookup: dict[str, dict] = {}  # type: ignore[type-arg]
        for i in range(MAX_EXTENDS_DEPTH + 1):
            uri = f"loom://cap-{i}"
            if i == 0:
                lookup[uri] = {"slug": f"cap-{i}", "steps": []}
            else:
                lookup[uri] = {
                    "slug": f"cap-{i}",
                    "extends": f"loom://cap-{i - 1}",
                    "steps": [],
                }

        # Chain of depth MAX_EXTENDS_DEPTH (11 layers, 10 extends hops)
        top_uri = f"loom://cap-{MAX_EXTENDS_DEPTH}"
        chain = resolver.resolve_extends_chain(top_uri, lookup)
        assert len(chain) == MAX_EXTENDS_DEPTH + 1

    def test_depth_limit_exceeded_raises(self, resolver: ExtendsResolver) -> None:
        """Chain deeper than MAX_EXTENDS_DEPTH raises ValueError."""
        from loom.extends.resolver import MAX_EXTENDS_DEPTH

        count = MAX_EXTENDS_DEPTH + 2  # one too many
        lookup: dict[str, dict] = {}  # type: ignore[type-arg]
        for i in range(count):
            uri = f"loom://cap-{i}"
            if i == 0:
                lookup[uri] = {"slug": f"cap-{i}", "steps": []}
            else:
                lookup[uri] = {
                    "slug": f"cap-{i}",
                    "extends": f"loom://cap-{i - 1}",
                    "steps": [],
                }

        top_uri = f"loom://cap-{count - 1}"
        with pytest.raises(ValueError, match="maximum depth"):
            resolver.resolve_extends_chain(top_uri, lookup)

    def test_missing_extends_target_raises(self, resolver: ExtendsResolver) -> None:
        lookup = {
            "loom://a": {"slug": "a", "extends": "loom://nonexistent", "steps": []},
        }
        with pytest.raises(ValueError, match="not found"):
            resolver.resolve_extends_chain("loom://a", lookup)


# ======================================================================
# Task 14: Append-only merge enforcement
# ======================================================================


class TestAppendOnlyEnforcement:
    """Preventing step substitution attacks via extends."""

    def test_reject_duplicate_skill_ref(self, resolver: ExtendsResolver) -> None:
        """Extension step with same skill_ref as base step is rejected."""
        layers = [
            {
                "slug": "base",
                "steps": [{"skill_ref": "loom://web-search", "role": "Search"}],
            },
            {
                "slug": "overlay",
                "steps": [{"skill_ref": "loom://web-search", "role": "Malicious search"}],
            },
        ]
        with pytest.raises(ValueError, match="cannot replace existing steps"):
            resolver.merge_capability_layers(layers)

    def test_reject_duplicate_role(self, resolver: ExtendsResolver) -> None:
        """Extension step with same role as base step is rejected."""
        layers = [
            {
                "slug": "base",
                "steps": [{"skill_ref": "loom://step-a", "role": "Shared role"}],
            },
            {
                "slug": "overlay",
                "steps": [{"skill_ref": "loom://step-b", "role": "Shared role"}],
            },
        ]
        with pytest.raises(ValueError, match="cannot replace existing steps"):
            resolver.merge_capability_layers(layers)

    def test_valid_new_steps_accepted(self, resolver: ExtendsResolver) -> None:
        """Extension with entirely new steps succeeds."""
        layers = [
            {
                "slug": "base",
                "steps": [
                    {"skill_ref": "loom://step-a", "role": "Role A"},
                    {"skill_ref": "loom://step-b", "role": "Role B"},
                ],
            },
            {
                "slug": "overlay",
                "steps": [
                    {"skill_ref": "loom://step-c", "role": "Role C"},
                    {"skill_ref": "loom://step-d", "role": "Role D"},
                ],
            },
        ]
        result = resolver.merge_capability_layers(layers)
        assert len(result.steps) == 4
        assert result.steps[0]["role"] == "Role A"
        assert result.steps[1]["role"] == "Role B"
        assert result.steps[2]["role"] == "Role C"
        assert result.steps[3]["role"] == "Role D"

    def test_base_steps_order_preserved(self, resolver: ExtendsResolver) -> None:
        """Base steps appear before extension steps in output."""
        layers = [
            {
                "slug": "base",
                "steps": [
                    {"skill_ref": "loom://first", "role": "First"},
                    {"skill_ref": "loom://second", "role": "Second"},
                ],
            },
            {
                "slug": "ext",
                "steps": [{"skill_ref": "loom://third", "role": "Third"}],
            },
        ]
        result = resolver.merge_capability_layers(layers)
        roles = [s["role"] for s in result.steps]
        assert roles == ["First", "Second", "Third"]

    def test_error_message_includes_conflicting_ref(self, resolver: ExtendsResolver) -> None:
        layers = [
            {
                "slug": "base",
                "steps": [{"skill_ref": "loom://target", "role": "R1"}],
            },
            {
                "slug": "ext",
                "steps": [{"skill_ref": "loom://target", "role": "R2"}],
            },
        ]
        with pytest.raises(ValueError, match="loom://target"):
            resolver.merge_capability_layers(layers)

    def test_error_message_includes_conflicting_role(self, resolver: ExtendsResolver) -> None:
        layers = [
            {
                "slug": "base",
                "steps": [{"skill_ref": "loom://s1", "role": "Duplicate role"}],
            },
            {
                "slug": "ext",
                "steps": [{"skill_ref": "loom://s2", "role": "Duplicate role"}],
            },
        ]
        with pytest.raises(ValueError, match="Duplicate role"):
            resolver.merge_capability_layers(layers)


# ======================================================================
# Task 15: Cross-source URI validation
# ======================================================================


class TestValidateStepSources:
    """URI prefix validation for capability step skill_refs."""

    def test_valid_loom_ref(self) -> None:
        steps = [{"skill_ref": "loom://web-search", "role": "Search"}]
        warnings = validate_step_sources(steps)
        assert warnings == []

    def test_valid_corp_ref_produces_warning(self) -> None:
        steps = [{"skill_ref": "corp://internal-tool", "role": "Internal"}]
        warnings = validate_step_sources(steps)
        assert len(warnings) == 1
        assert "not resolvable in a public context" in warnings[0]
        assert "internal-tool" in warnings[0]

    def test_missing_prefix_raises(self) -> None:
        steps = [{"skill_ref": "bare-slug", "role": "No prefix"}]
        with pytest.raises(ValueError, match="missing a URI scheme prefix"):
            validate_step_sources(steps)

    def test_empty_skill_ref_raises(self) -> None:
        steps = [{"skill_ref": "", "role": "Empty"}]
        with pytest.raises(ValueError, match="missing a URI scheme prefix"):
            validate_step_sources(steps)

    def test_unsupported_scheme_raises(self) -> None:
        steps = [{"skill_ref": "http://example.com/skill", "role": "Web"}]
        with pytest.raises(ValueError, match="unsupported URI scheme"):
            validate_step_sources(steps)

    def test_mixed_valid_refs(self) -> None:
        steps = [
            {"skill_ref": "loom://step-a", "role": "A"},
            {"skill_ref": "corp://step-b", "role": "B"},
            {"skill_ref": "loom://step-c", "role": "C"},
        ]
        warnings = validate_step_sources(steps)
        assert len(warnings) == 1  # only the corp:// ref
        assert "step-b" in warnings[0]

    def test_multiple_corp_refs_produce_multiple_warnings(self) -> None:
        steps = [
            {"skill_ref": "corp://tool-1", "role": "T1"},
            {"skill_ref": "corp://tool-2", "role": "T2"},
        ]
        warnings = validate_step_sources(steps)
        assert len(warnings) == 2

    def test_no_steps_returns_empty(self) -> None:
        assert validate_step_sources([]) == []
