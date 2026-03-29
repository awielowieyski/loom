"""CapabilityRegistryService: create, retrieve, update and list capabilities."""

import logging
import uuid as uuid_mod
from typing import TYPE_CHECKING, Any

from loom.models.capability import (
    Capability,
    CapabilityCreate,
    CapabilityStep,
    CapabilitySummary,
    CapabilityUpdate,
    DataFlowEdge,
)
from loom.models.common import (
    CostProfile,
    DependencyDeclaration,
    EstimatedDuration,
    TrustTier,
)

if TYPE_CHECKING:
    from loom.db.repositories.capability_repo import CapabilityRepo
    from loom.db.repositories.category_repo import CategoryRepo


def _coerce_duration(value: EstimatedDuration | str | None, fallback: str) -> str:
    """Safely extract a string value from an EstimatedDuration, str, or None."""
    if value is None:
        return fallback
    return value.value if isinstance(value, EstimatedDuration) else str(value)


def _coerce_cost_profile(value: CostProfile | str | None, fallback: CostProfile) -> CostProfile:
    """Coerce a CostProfile value, returning the fallback when None."""
    if value is None:
        return fallback
    return value if isinstance(value, CostProfile) else CostProfile(value)


logger = logging.getLogger(__name__)


class CapabilityRegistryService:
    """Orchestrates capability registration with structural validation."""

    def __init__(
        self,
        capability_repo: "CapabilityRepo",
        category_repo: "CategoryRepo",
        embedder: Any,
    ) -> None:
        self._capability_repo = capability_repo
        self._category_repo = category_repo
        self._embedder = embedder

    async def create_capability(
        self,
        data: CapabilityCreate,
        author_id: uuid_mod.UUID,
        embedding: list[float] | None = None,
    ) -> Capability:
        """Validate, resolve category, then create capability + initial version."""
        # Validate steps
        warnings = self._validate_steps(data.steps)
        for w in warnings:
            logger.warning("Step validation: %s", w)

        # Validate data flow
        errors = self._validate_data_flow(data.steps, data.data_flow)
        if errors:
            raise ValueError(f"Data flow validation failed: {'; '.join(errors)}")

        # Resolve category
        category = await self._category_repo.get_by_slug(data.category_slug)
        if category is None:
            raise ValueError(f"Category not found: {data.category_slug!r}")

        return await self._capability_repo.create(
            slug=data.slug,
            name=data.name,
            description=data.description,
            category_id=category.id,
            tags=data.tags,
            version=data.version,
            author_id=author_id,
            steps=data.steps,
            preconditions=data.preconditions,
            expected_outcome=data.expected_outcome,
            data_flow=data.data_flow,
            dependencies=data.dependencies,
            eval_spec=data.eval_spec,
            scope=data.scope,
            trust_tier=data.trust_tier,
            cost_profile=data.cost_profile,
            cost_drivers=data.cost_drivers,
            estimated_duration=_coerce_duration(data.estimated_duration, "slow"),
            extends=data.extends,
            embedding=embedding,
            lifecycle_state=data.lifecycle_state,
            provenance_summary=data.provenance_summary,
        )

    async def get_capability(self, slug: str, version: str | None = None) -> Capability | None:
        """Return a capability by slug, optionally at a specific version."""
        capability = await self._capability_repo.get_by_slug(slug)
        if capability is None or version is None:
            return capability

        ver = await self._capability_repo.get_version(capability.id, version)
        if ver is None:
            return None

        # Overlay version-specific fields onto the capability.
        # For each optional version field, fall back to the capability's value.
        def _pick(ver_val: object, cap_val: object) -> object:
            return ver_val if ver_val is not None else cap_val

        return capability.model_copy(
            update={
                "version": ver.version,
                "steps": ver.steps,
                "preconditions": _pick(ver.preconditions, capability.preconditions),
                "expected_outcome": _pick(ver.expected_outcome, capability.expected_outcome),
                "data_flow": _pick(ver.data_flow, capability.data_flow),
                "dependencies": _pick(ver.dependencies, capability.dependencies),
                "cost_profile": (
                    CostProfile(ver.cost_profile)
                    if ver.cost_profile is not None
                    else capability.cost_profile
                ),
                "cost_drivers": _pick(ver.cost_drivers, capability.cost_drivers),
                "estimated_duration": _pick(ver.estimated_duration, capability.estimated_duration),
                "eval_spec": _pick(ver.eval_spec, capability.eval_spec),
                "extends": _pick(ver.extends, capability.extends),
            },
        )

    async def update_capability(
        self,
        slug: str,
        data: CapabilityUpdate,
        author_id: uuid_mod.UUID,
    ) -> Capability:
        """Merge new values over existing capability, create version record."""
        existing = await self._capability_repo.get_by_slug(slug)
        if existing is None:
            raise ValueError(f"Capability not found: {slug!r}")

        # Merge: new values override existing where provided
        steps = data.steps if data.steps is not None else existing.steps
        description = data.description if data.description is not None else existing.description
        tags = data.tags if data.tags is not None else existing.tags
        preconditions = (
            data.preconditions if data.preconditions is not None else existing.preconditions
        )
        expected_outcome = (
            data.expected_outcome
            if data.expected_outcome is not None
            else existing.expected_outcome
        )
        data_flow = data.data_flow if data.data_flow is not None else existing.data_flow
        dependencies = data.dependencies if data.dependencies is not None else existing.dependencies
        cost_profile = _coerce_cost_profile(data.cost_profile, existing.cost_profile)
        cost_drivers = data.cost_drivers if data.cost_drivers is not None else existing.cost_drivers
        estimated_duration = _coerce_duration(data.estimated_duration, existing.estimated_duration)
        eval_spec = data.eval_spec if data.eval_spec is not None else existing.eval_spec
        extends = data.extends if "extends" in data.model_fields_set else existing.extends

        # Validate steps if changed
        if data.steps is not None:
            warnings = self._validate_steps(steps)
            for w in warnings:
                logger.warning("Step validation: %s", w)

        # Validate data flow if steps or data_flow changed
        if data.steps is not None or data.data_flow is not None:
            errors = self._validate_data_flow(steps, data_flow)
            if errors:
                raise ValueError(f"Data flow validation failed: {'; '.join(errors)}")

        updated = await self._capability_repo.update(
            existing.id,
            version=data.version,
            author_id=author_id,
            steps=steps,
            description=description,
            tags=tags,
            preconditions=preconditions,
            expected_outcome=expected_outcome,
            data_flow=data_flow,
            dependencies=dependencies,
            cost_profile=cost_profile,
            cost_drivers=cost_drivers,
            estimated_duration=estimated_duration,
            eval_spec=eval_spec,
            extends=extends,
            changelog=data.changelog,
            fields_set=data.model_fields_set,
        )
        if updated is None:
            raise ValueError(f"Update failed for capability: {slug!r}")

        return updated

    async def list_capabilities(
        self,
        trust_tier: TrustTier | None = None,
    ) -> list[CapabilitySummary]:
        """Return capability summaries with optional filters."""
        return await self._capability_repo.list_all(trust_tier=trust_tier)

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_steps(steps: list[CapabilityStep]) -> list[str]:
        """Validate step skill_ref URIs. Raises ValueError for structural issues.

        Returns a list of warnings (e.g. non-resolvable corp:// refs).
        """
        warnings: list[str] = []

        for idx, step in enumerate(steps):
            ref = step.skill_ref
            if "://" not in ref:
                raise ValueError(
                    f"Step {idx} skill_ref {ref!r} is missing a URI scheme prefix "
                    f"(expected e.g. 'loom://slug')"
                )

            scheme, slug = ref.split("://", 1)
            if not slug:
                raise ValueError(f"Step {idx} skill_ref {ref!r} has an empty slug")

            if scheme.lower() == "corp":
                warnings.append(
                    f"Step {idx} references corp://{slug} which is not "
                    f"resolvable in a public context"
                )

        return warnings

    @staticmethod
    def _validate_data_flow(
        steps: list[CapabilityStep], data_flow: list[DataFlowEdge]
    ) -> list[str]:
        """Validate data flow edges against the step list.

        Returns a list of error messages. An empty list means valid.
        """
        if not data_flow:
            return []

        valid_classifications = {"internal", "external", "confidential"}
        errors: list[str] = []

        # Build slug-to-index map from steps (slug is the part after ://)
        slug_to_index: dict[str, int] = {}
        for idx, step in enumerate(steps):
            ref = step.skill_ref
            if "://" in ref:
                slug = ref.split("://", 1)[1]
                if slug in slug_to_index:
                    errors.append(
                        f"Duplicate step slug {slug!r} at indices {slug_to_index[slug]} and {idx}; "
                        f"data flow edges cannot distinguish between them"
                    )
                slug_to_index[slug] = idx

        for edge_idx, edge in enumerate(data_flow):
            # Validate from_step exists
            if edge.from_step not in slug_to_index:
                errors.append(
                    f"Data flow edge {edge_idx}: from_step {edge.from_step!r} "
                    f"does not reference a known step slug"
                )
            # Validate to_step exists
            if edge.to_step not in slug_to_index:
                errors.append(
                    f"Data flow edge {edge_idx}: to_step {edge.to_step!r} "
                    f"does not reference a known step slug"
                )

            # Validate forward-only (only if both steps are valid)
            if edge.from_step in slug_to_index and edge.to_step in slug_to_index:
                from_idx = slug_to_index[edge.from_step]
                to_idx = slug_to_index[edge.to_step]
                if from_idx >= to_idx:
                    errors.append(
                        f"Data flow edge {edge_idx}: backward or self-referencing flow "
                        f"from step {edge.from_step!r} (index {from_idx}) "
                        f"to step {edge.to_step!r} (index {to_idx})"
                    )

            # Validate classification
            if edge.classification not in valid_classifications:
                errors.append(
                    f"Data flow edge {edge_idx}: invalid classification "
                    f"{edge.classification!r}, must be one of {sorted(valid_classifications)}"
                )

        return errors

    @staticmethod
    def aggregate_dependencies(
        steps: list[CapabilityStep],
        skill_deps: list[DependencyDeclaration],
    ) -> DependencyDeclaration:
        """Aggregate dependencies from all steps into a single declaration.

        - MCP server deps are deduplicated by URI
        - API deps are deduplicated by name
        - Trust requirements: highest data_classification, network_access = any step needs it
        """
        from loom.models.common import (
            APIDependency,
            MCPServerDependency,
            TrustRequirements,
        )

        seen_mcp_uris: dict[str, MCPServerDependency] = {}
        seen_api_names: dict[str, APIDependency] = {}

        classification_rank = {"none": 0, "internal": 1, "confidential": 2}
        highest_classification = "none"
        network_access = False

        for dep in skill_deps:
            # MCP servers — deduplicate by URI
            for mcp in dep.mcp_servers:
                if mcp.uri not in seen_mcp_uris:
                    seen_mcp_uris[mcp.uri] = mcp

            # APIs — deduplicate by name
            for api in dep.apis:
                if api.name not in seen_api_names:
                    seen_api_names[api.name] = api

            # Trust requirements
            tr = dep.trust_requirements
            if classification_rank.get(tr.data_classification, 0) > classification_rank.get(
                highest_classification, 0
            ):
                highest_classification = tr.data_classification
            if tr.network_access:
                network_access = True

        return DependencyDeclaration(
            mcp_servers=list(seen_mcp_uris.values()),
            apis=list(seen_api_names.values()),
            trust_requirements=TrustRequirements(
                data_classification=highest_classification,
                network_access=network_access,
            ),
        )
