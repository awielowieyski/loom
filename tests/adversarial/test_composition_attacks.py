"""Adversarial test suite for M3 composition security attacks.

Covers all 6 threats from the M3 Composition Security Spec (Section 6):
  Threat 1: Injection via extends chain (trust laundering)
  Threat 2: Dependency confusion (source shadowing)
  Threat 3: Data flow injection
  Threat 4: Privilege escalation via composition (trust laundering)
  Threat 5: Step substitution via extends
  Threat 6: Circular extends
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest

from loom.extends.resolver import MAX_EXTENDS_DEPTH, ExtendsResolver
from loom.models.capability import (
    Capability,
    CapabilityStep,
    CapabilitySummary,
    DataFlowEdge,
)
from loom.models.common import (
    CostProfile,
    DependencyDeclaration,
    EvalSpec,
    TrustTier,
)
from loom.models.resolution import ResolutionContext, ResolutionError
from loom.services.capability_discovery import CapabilityDiscoveryService
from tests.helpers import make_test_skill

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CAT_ID = uuid.uuid4()
_AUTHOR_ID = uuid.uuid4()


def _make_capability(**overrides) -> Capability:
    """Create a Capability with sensible defaults for testing."""
    defaults = {
        "id": uuid.uuid4(),
        "slug": "test-capability",
        "name": "Test Capability",
        "description": "A capability for testing.",
        "category_id": _CAT_ID,
        "tags": [],
        "scope": "community",
        "version": "1.0.0",
        "author_id": _AUTHOR_ID,
        "trust_tier": TrustTier.COMMUNITY,
        "steps": [
            CapabilityStep(
                skill_ref="loom://test-skill",
                role="Do something",
                inputs={},
                outputs={},
            )
        ],
        "preconditions": [],
        "expected_outcome": "Test outcome",
        "data_flow": [],
        "dependencies": DependencyDeclaration(),
        "cost_profile": CostProfile.FREE,
        "cost_drivers": [],
        "estimated_duration": "fast",
        "eval_spec": EvalSpec(),
    }
    defaults.update(overrides)
    return Capability(**defaults)


def _make_capability_summary(cap: Capability) -> CapabilitySummary:
    return cap.to_summary()


def _make_discovery_service(
    capability: Capability,
    skills: dict[str, dict],
) -> CapabilityDiscoveryService:
    """Build a CapabilityDiscoveryService with mocked repos and embedder.

    Args:
        capability: The capability to return from vector search.
        skills: Mapping of slug -> skill override kwargs for make_test_skill.
    """
    summary = _make_capability_summary(capability)

    cap_repo = AsyncMock()
    cap_repo.vector_search_summary = AsyncMock(return_value=[summary])
    cap_repo.get_by_id = AsyncMock(return_value=capability)

    skill_repo = AsyncMock()

    async def _get_by_slug(slug: str, version: str | None = None):
        if slug in skills:
            return make_test_skill(slug=slug, **skills[slug])
        return None

    skill_repo.get_by_slug = AsyncMock(side_effect=_get_by_slug)

    embedder = AsyncMock()
    embedder.embed_query = AsyncMock(return_value=AsyncMock(embeddings=[[0.1] * 10]))

    return CapabilityDiscoveryService(
        capability_repo=cap_repo,
        skill_repo=skill_repo,
        embedder=embedder,
    )


# ===========================================================================
# Threat 1 & 4: Trust Laundering
# ===========================================================================


class TestTrustLaundering:
    """Verify minimum-trust propagation prevents trust laundering."""

    @pytest.mark.asyncio
    async def test_effective_trust_is_min_across_steps(self):
        """A capability mixing experimental and verified skills
        must report effective_trust_tier = experimental (the minimum)."""
        cap = _make_capability(
            slug="mixed-trust",
            trust_tier=TrustTier.VERIFIED,
            steps=[
                CapabilityStep(
                    skill_ref="loom://verified-skill",
                    role="Verified step",
                ),
                CapabilityStep(
                    skill_ref="loom://experimental-skill",
                    role="Experimental step",
                ),
            ],
        )

        svc = _make_discovery_service(
            cap,
            skills={
                "verified-skill": {"trust_tier": TrustTier.VERIFIED},
                "experimental-skill": {"trust_tier": TrustTier.EXPERIMENTAL},
            },
        )

        result = await svc.resolve("mixed trust test")
        assert not isinstance(result, ResolutionError), result.message
        assert result.effective_trust_tier == TrustTier.EXPERIMENTAL

    @pytest.mark.asyncio
    async def test_trust_floor_rejects_capability_with_experimental_step(self):
        """Resolving with trust_floor=community must reject a capability
        that contains an experimental-tier step skill."""
        cap = _make_capability(
            slug="looks-community",
            trust_tier=TrustTier.COMMUNITY,
            steps=[
                CapabilityStep(
                    skill_ref="loom://community-skill",
                    role="Community step",
                ),
                CapabilityStep(
                    skill_ref="loom://sneaky-experimental",
                    role="Sneaky experimental step",
                ),
            ],
        )

        svc = _make_discovery_service(
            cap,
            skills={
                "community-skill": {"trust_tier": TrustTier.COMMUNITY},
                "sneaky-experimental": {"trust_tier": TrustTier.EXPERIMENTAL},
            },
        )

        context = ResolutionContext(trust_floor=TrustTier.COMMUNITY)
        result = await svc.resolve("trust floor test", context=context)

        assert isinstance(result, ResolutionError)
        assert "experimental" in result.message.lower()

    @pytest.mark.asyncio
    async def test_trust_warnings_list_offending_steps(self):
        """Trust warnings should name the specific experimental step."""
        cap = _make_capability(
            slug="warning-test",
            trust_tier=TrustTier.VERIFIED,
            steps=[
                CapabilityStep(
                    skill_ref="loom://good-skill",
                    role="Good step",
                ),
                CapabilityStep(
                    skill_ref="loom://bad-skill",
                    role="Bad step",
                ),
            ],
        )

        svc = _make_discovery_service(
            cap,
            skills={
                "good-skill": {"trust_tier": TrustTier.VERIFIED},
                "bad-skill": {"trust_tier": TrustTier.EXPERIMENTAL},
            },
        )

        result = await svc.resolve("warnings test")
        assert not isinstance(result, ResolutionError)
        assert any("bad-skill" in w for w in result.trust_warnings)


# ===========================================================================
# Threat 2: Dependency Confusion
# ===========================================================================


class TestDependencyConfusion:
    """Verify mandatory URI prefixes prevent source shadowing."""

    def test_bare_slug_rejected_at_creation(self):
        """A step with a bare slug (no URI prefix) must be rejected
        by the CapabilityStep validator."""
        with pytest.raises(ValueError, match="URI scheme prefix"):
            CapabilityStep(
                skill_ref="web-search",
                role="Search the web",
            )

    def test_slug_without_scheme_rejected(self):
        """Even plausible-looking refs without :// are rejected."""
        with pytest.raises(ValueError, match="URI scheme prefix"):
            CapabilityStep(
                skill_ref="search",
                role="Search",
            )

    @pytest.mark.asyncio
    async def test_loom_ref_resolves_from_skill_repo_not_corp(self):
        """A loom:// ref must resolve from the public skill_repo.
        The skill_repo mock is called with the correct slug."""
        cap = _make_capability(
            steps=[
                CapabilityStep(
                    skill_ref="loom://web-search",
                    role="Search",
                ),
            ],
        )

        skill_repo = AsyncMock()
        skill_repo.get_by_slug = AsyncMock(return_value=make_test_skill(slug="web-search"))

        cap_repo = AsyncMock()
        cap_repo.vector_search_summary = AsyncMock(return_value=[_make_capability_summary(cap)])
        cap_repo.get_by_id = AsyncMock(return_value=cap)

        embedder = AsyncMock()
        embedder.embed_query = AsyncMock(return_value=AsyncMock(embeddings=[[0.1] * 10]))

        svc = CapabilityDiscoveryService(
            capability_repo=cap_repo,
            skill_repo=skill_repo,
            embedder=embedder,
        )

        result = await svc.resolve("search test")
        assert not isinstance(result, ResolutionError)

        # Verify skill_repo was called with the parsed slug
        skill_repo.get_by_slug.assert_awaited_once_with("web-search", version=None)

    @pytest.mark.asyncio
    async def test_corp_ref_returns_placeholder_not_public_skill(self):
        """A corp:// ref on public Loom must NOT resolve from skill_repo.
        It should return a placeholder instead."""
        cap = _make_capability(
            steps=[
                CapabilityStep(
                    skill_ref="corp://internal-tool",
                    role="Internal corporate tool",
                ),
            ],
        )

        skill_repo = AsyncMock()
        # This should NOT be called for corp:// refs
        skill_repo.get_by_slug = AsyncMock(return_value=make_test_skill(slug="internal-tool"))

        cap_repo = AsyncMock()
        cap_repo.vector_search_summary = AsyncMock(return_value=[_make_capability_summary(cap)])
        cap_repo.get_by_id = AsyncMock(return_value=cap)

        embedder = AsyncMock()
        embedder.embed_query = AsyncMock(return_value=AsyncMock(embeddings=[[0.1] * 10]))

        svc = CapabilityDiscoveryService(
            capability_repo=cap_repo,
            skill_repo=skill_repo,
            embedder=embedder,
        )

        result = await svc.resolve("corp test")
        assert not isinstance(result, ResolutionError)

        # skill_repo.get_by_slug should NOT have been called — corp resolves
        # to a placeholder, not through the public registry
        skill_repo.get_by_slug.assert_not_awaited()


# ===========================================================================
# Threat 3: Data Flow Injection
# ===========================================================================


class TestDataFlowInjection:
    """Verify external data flow classification produces safety warnings."""

    @pytest.mark.asyncio
    async def test_external_data_flow_produces_warning(self):
        """When a capability has an external data flow edge, the resolved
        plan's selection_rationale must include a safety warning."""
        cap = _make_capability(
            slug="external-flow",
            steps=[
                CapabilityStep(
                    skill_ref="loom://web-search",
                    role="Fetch data from the web",
                    data_classification="external",
                ),
                CapabilityStep(
                    skill_ref="loom://synthesise",
                    role="Synthesise results",
                ),
            ],
            data_flow=[
                DataFlowEdge(
                    from_step="web-search",
                    to_step="synthesise",
                    classification="external",
                ),
            ],
        )

        svc = _make_discovery_service(
            cap,
            skills={
                "web-search": {},
                "synthesise": {},
            },
        )

        result = await svc.resolve("external flow test")
        assert not isinstance(result, ResolutionError)

        # selection_rationale should warn about external data flow
        rationale_text = " ".join(result.selection_rationale)
        assert "external" in rationale_text.lower()
        assert "untrusted" in rationale_text.lower()

    @pytest.mark.asyncio
    async def test_external_warning_references_specific_steps(self):
        """The warning must reference the specific from_step and to_step."""
        cap = _make_capability(
            slug="specific-warning",
            steps=[
                CapabilityStep(
                    skill_ref="loom://fetcher",
                    role="Fetch external data",
                    data_classification="external",
                ),
                CapabilityStep(
                    skill_ref="loom://processor",
                    role="Process fetched data",
                ),
            ],
            data_flow=[
                DataFlowEdge(
                    from_step="fetcher",
                    to_step="processor",
                    classification="external",
                ),
            ],
        )

        svc = _make_discovery_service(
            cap,
            skills={
                "fetcher": {},
                "processor": {},
            },
        )

        result = await svc.resolve("specific warning test")
        assert not isinstance(result, ResolutionError)

        rationale_text = " ".join(result.selection_rationale)
        assert "fetcher" in rationale_text
        assert "processor" in rationale_text


# ===========================================================================
# Threat 5: Step Substitution via Extends
# ===========================================================================


class TestStepSubstitution:
    """Verify append-only merge prevents step replacement through extends."""

    def setup_method(self):
        self.resolver = ExtendsResolver()

    def test_replace_step_by_skill_ref_rejected(self):
        """An extending capability that defines a step with the same
        skill_ref as a base step must be rejected."""
        base_layer = {
            "steps": [
                {"skill_ref": "loom://review-pull-request", "role": "Base review"},
            ],
            "source": "loom",
            "slug": "base-cap",
        }
        extension_layer = {
            "steps": [
                {"skill_ref": "loom://review-pull-request", "role": "Malicious replacement"},
            ],
            "source": "corp",
            "slug": "evil-overlay",
        }

        with pytest.raises(ValueError, match="cannot replace existing steps"):
            self.resolver.merge_capability_layers([base_layer, extension_layer])

    def test_replace_step_by_role_rejected(self):
        """An extending capability that defines a step with the same
        role as a base step must be rejected."""
        base_layer = {
            "steps": [
                {"skill_ref": "loom://tool-a", "role": "Shared role name"},
            ],
            "source": "loom",
            "slug": "base-cap",
        }
        extension_layer = {
            "steps": [
                {"skill_ref": "loom://tool-b", "role": "Shared role name"},
            ],
            "source": "corp",
            "slug": "evil-overlay",
        }

        with pytest.raises(ValueError, match="cannot replace existing steps"):
            self.resolver.merge_capability_layers([base_layer, extension_layer])

    def test_append_only_new_steps_succeeds(self):
        """Extending with genuinely new steps (different skill_ref and role)
        must succeed and produce merged output."""
        base_layer = {
            "steps": [
                {"skill_ref": "loom://step-a", "role": "Step A"},
            ],
            "preconditions": ["Base precondition"],
            "expected_outcome": "Base outcome",
            "data_flow": [],
            "source": "loom",
            "slug": "base-cap",
        }
        extension_layer = {
            "steps": [
                {"skill_ref": "loom://step-b", "role": "Step B"},
                {"skill_ref": "loom://step-c", "role": "Step C"},
            ],
            "preconditions": ["Extension precondition"],
            "expected_outcome": "Extended outcome",
            "data_flow": [],
            "source": "corp",
            "slug": "ext-cap",
        }

        result = self.resolver.merge_capability_layers([base_layer, extension_layer])
        assert len(result.steps) == 3
        assert result.steps[0]["skill_ref"] == "loom://step-a"
        assert result.steps[1]["skill_ref"] == "loom://step-b"
        assert result.steps[2]["skill_ref"] == "loom://step-c"
        assert "Base precondition" in result.preconditions
        assert "Extension precondition" in result.preconditions
        assert result.expected_outcome == "Extended outcome"


# ===========================================================================
# Threat 6: Circular Extends
# ===========================================================================


class TestCircularExtends:
    """Verify cycle detection prevents infinite extends resolution."""

    def setup_method(self):
        self.resolver = ExtendsResolver()

    def test_direct_cycle_detected(self):
        """A extends B extends A must raise a cycle error."""
        lookup = {
            "loom://a": {
                "steps": [{"skill_ref": "loom://s1", "role": "S1"}],
                "extends": "loom://b",
            },
            "loom://b": {
                "steps": [{"skill_ref": "loom://s2", "role": "S2"}],
                "extends": "loom://a",
            },
        }

        with pytest.raises(ValueError, match="[Cc]ircular extends"):
            self.resolver.resolve_extends_chain("loom://a", lookup)

    def test_transitive_cycle_detected(self):
        """A extends B extends C extends A must raise a cycle error
        with the full chain described."""
        lookup = {
            "loom://a": {
                "steps": [{"skill_ref": "loom://s1", "role": "S1"}],
                "extends": "loom://b",
            },
            "loom://b": {
                "steps": [{"skill_ref": "loom://s2", "role": "S2"}],
                "extends": "loom://c",
            },
            "loom://c": {
                "steps": [{"skill_ref": "loom://s3", "role": "S3"}],
                "extends": "loom://a",
            },
        }

        with pytest.raises(ValueError, match="[Cc]ircular extends"):
            self.resolver.resolve_extends_chain("loom://a", lookup)

    def test_max_depth_exceeded(self):
        """A chain deeper than MAX_EXTENDS_DEPTH must be rejected."""
        # Build a chain of depth MAX_EXTENDS_DEPTH + 2 (no cycles)
        lookup = {}
        for i in range(MAX_EXTENDS_DEPTH + 2):
            uri = f"loom://cap-{i}"
            parent = f"loom://cap-{i + 1}" if i < MAX_EXTENDS_DEPTH + 1 else None
            lookup[uri] = {
                "steps": [{"skill_ref": f"loom://skill-{i}", "role": f"Role {i}"}],
            }
            if parent:
                lookup[uri]["extends"] = parent

        with pytest.raises(ValueError, match="maximum depth"):
            self.resolver.resolve_extends_chain("loom://cap-0", lookup)

    def test_valid_chain_resolves(self):
        """A non-cyclic chain within depth limits resolves successfully."""
        lookup = {
            "loom://a": {
                "steps": [{"skill_ref": "loom://s1", "role": "S1"}],
                "extends": "loom://b",
            },
            "loom://b": {
                "steps": [{"skill_ref": "loom://s2", "role": "S2"}],
                "extends": "loom://c",
            },
            "loom://c": {
                "steps": [{"skill_ref": "loom://s3", "role": "S3"}],
            },
        }

        layers = self.resolver.resolve_extends_chain("loom://a", lookup)
        # Should be: c (base), b, a
        assert len(layers) == 3
        assert layers[0] is lookup["loom://c"]
        assert layers[1] is lookup["loom://b"]
        assert layers[2] is lookup["loom://a"]
