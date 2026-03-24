"""Client-side extends resolver for merging skill and capability layers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Maximum depth for extends chains (prevents infinite recursion)
MAX_EXTENDS_DEPTH = 10

# Valid URI scheme prefixes for step skill references
VALID_URI_SCHEMES = {"loom", "corp"}


@dataclass
class LayerInfo:
    """Metadata about a single skill layer."""

    source: str
    slug: str
    version: str | None
    content: str


@dataclass
class ResolvedChain:
    """Result of merging one or more skill layers."""

    merged_content: str
    layers: list[LayerInfo] = field(default_factory=list)


@dataclass
class ResolvedCapabilityChain:
    """Result of merging one or more capability layers (append-only)."""

    steps: list[dict[str, Any]] = field(default_factory=list)
    preconditions: list[str] = field(default_factory=list)
    expected_outcome: str = ""
    data_flow: list[dict[str, Any]] = field(default_factory=list)
    layers: list[LayerInfo] = field(default_factory=list)


# Delimiters inserted between layers based on source type
_LAYER_HEADERS: dict[str, str] = {
    "loom": "",  # base layer — no header
    "corp": "## Corporate Context",
    "local": "## Local Overrides",
}

_DEFAULT_SUBSEQUENT_HEADER = "## Layer Override"


def _header_for_index(index: int, source: str) -> str:
    """Return the delimiter header for a given layer position and source."""
    if index == 0:
        return ""
    return _LAYER_HEADERS.get(source, _DEFAULT_SUBSEQUENT_HEADER)


class ExtendsResolver:
    """Merge skill layers declared via extends URIs (client-side only)."""

    def merge_layers(self, layers: list[dict[str, object]]) -> ResolvedChain:
        """Merge a list of layer dicts into a single ResolvedChain.

        Each dict must contain at least ``content``, and optionally
        ``source``, ``slug``, and ``version`` keys.

        Layers are joined with appropriate section headers:
        - First layer (community base): no header
        - Subsequent ``corp://`` layers: ``## Corporate Context``
        - Subsequent ``local://`` layers: ``## Local Overrides``
        - All others: ``## Layer Override``
        """
        layer_infos: list[LayerInfo] = []
        parts: list[str] = []

        for i, layer in enumerate(layers):
            content = str(layer.get("content", ""))
            source = str(layer.get("source", "loom"))
            slug = str(layer.get("slug", ""))
            raw_version = layer.get("version")
            version: str | None = str(raw_version) if raw_version is not None else None

            header = _header_for_index(i, source)

            if header:
                parts.append(header)
            parts.append(content)

            layer_infos.append(
                LayerInfo(source=source, slug=slug, version=version, content=content)
            )

        merged = "\n\n".join(p for p in parts if p)
        return ResolvedChain(merged_content=merged, layers=layer_infos)

    def parse_extends_uri(self, uri: str) -> tuple[str, str, str | None]:
        """Parse a ``loom://slug@version`` or ``corp://slug@version`` URI.

        Returns a tuple of ``(source, slug, version)`` where ``version``
        may be ``None`` if not specified.

        Raises:
            ValueError: if the URI scheme is missing or malformed.
        """
        if "://" not in uri:
            raise ValueError(f"Invalid extends URI (missing scheme): {uri!r}")

        scheme, rest = uri.split("://", 1)
        source = scheme.lower()

        if source not in VALID_URI_SCHEMES:
            raise ValueError(
                f"Unsupported URI scheme {source!r} in extends URI {uri!r}. "
                f"Supported: {', '.join(sorted(VALID_URI_SCHEMES))}"
            )

        if "@" in rest:
            slug, version = rest.rsplit("@", 1)
        else:
            slug = rest
            version = None

        if not slug:
            raise ValueError(f"Invalid extends URI (empty slug): {uri!r}")

        return source, slug, version

    # ------------------------------------------------------------------
    # Capability extends — append-only merge
    # ------------------------------------------------------------------

    def merge_capability_layers(self, layers: list[dict[str, Any]]) -> ResolvedCapabilityChain:
        """Merge capability layers using append-only semantics.

        Each layer dict must contain:
        - ``steps``: list of step dicts (each with at least ``skill_ref``, ``role``)
        - ``preconditions``: list[str] (optional)
        - ``expected_outcome``: str (optional)
        - ``data_flow``: list of edge dicts (optional)
        - ``source``, ``slug``, ``version``: layer metadata (optional)

        First layer's steps form the base.  Subsequent layers' steps are
        **appended** — any step whose ``skill_ref`` or ``role`` matches a
        base step is rejected (append-only enforcement, see Threat 5).

        Preconditions are concatenated across layers.
        Expected outcome uses the last layer's value if non-empty.
        Data flow edges are concatenated.
        """
        if not layers:
            return ResolvedCapabilityChain()

        all_steps: list[dict[str, Any]] = []
        all_preconditions: list[str] = []
        expected_outcome = ""
        all_data_flow: list[dict[str, Any]] = []
        layer_infos: list[LayerInfo] = []

        # Track base identity keys for append-only enforcement
        seen_skill_refs: set[str] = set()
        seen_roles: set[str] = set()

        for i, layer in enumerate(layers):
            source = str(layer.get("source", "loom"))
            slug = str(layer.get("slug", ""))
            raw_version = layer.get("version")
            version: str | None = str(raw_version) if raw_version is not None else None

            steps: list[dict[str, Any]] = list(layer.get("steps") or [])
            preconditions: list[str] = list(layer.get("preconditions") or [])
            outcome: str = str(layer.get("expected_outcome", ""))
            data_flow: list[dict[str, Any]] = list(layer.get("data_flow") or [])

            if i == 0:
                # Base layer — accept all steps and seed identity sets
                all_steps.extend(steps)
                for step in steps:
                    seen_skill_refs.add(step.get("skill_ref", ""))
                    seen_roles.add(step.get("role", ""))
            else:
                # Extension layer — enforce append-only
                for step in steps:
                    ref = step.get("skill_ref", "")
                    role = step.get("role", "")
                    if ref and ref in seen_skill_refs:
                        raise ValueError(
                            "Capability extends cannot replace existing steps. "
                            "Create a new version instead. "
                            f"Conflicting skill_ref: {ref}"
                        )
                    if role and role in seen_roles:
                        raise ValueError(
                            "Capability extends cannot replace existing steps. "
                            "Create a new version instead. "
                            f"Conflicting role: {role}"
                        )
                    seen_skill_refs.add(ref)
                    seen_roles.add(role)
                all_steps.extend(steps)

            all_preconditions.extend(preconditions)
            if outcome:
                expected_outcome = outcome
            all_data_flow.extend(data_flow)

            layer_infos.append(
                LayerInfo(
                    source=source,
                    slug=slug,
                    version=version,
                    content=f"{len(steps)} steps",
                )
            )

        return ResolvedCapabilityChain(
            steps=all_steps,
            preconditions=all_preconditions,
            expected_outcome=expected_outcome,
            data_flow=all_data_flow,
            layers=layer_infos,
        )

    # ------------------------------------------------------------------
    # Cycle detection for extends chains
    # ------------------------------------------------------------------

    def resolve_extends_chain(
        self,
        uri: str,
        lookup: dict[str, dict[str, Any]],
        *,
        visited: set[str] | None = None,
        depth: int = 0,
    ) -> list[dict[str, Any]]:
        """Walk an extends chain, returning layers in resolution order.

        ``lookup`` maps URIs to layer dicts (each must have at least
        ``steps`` and optionally ``extends``).

        Raises :class:`ValueError` on cycles or excessive depth.
        """
        if visited is None:
            visited = set()

        if depth > MAX_EXTENDS_DEPTH:
            raise ValueError(f"Extends chain exceeds maximum depth of {MAX_EXTENDS_DEPTH}")

        if uri in visited:
            chain = " -> ".join(visited) + " -> " + uri
            raise ValueError(f"Circular extends chain detected: {chain}. Remove the cycle.")

        layer = lookup.get(uri)
        if layer is None:
            raise ValueError(f"Extends target not found: {uri!r}")

        parent_uri = layer.get("extends")
        if parent_uri and isinstance(parent_uri, str):
            # Resolve parent first (bottom-up); copy-on-recurse for diamond DAG safety
            parent_layers = self.resolve_extends_chain(
                parent_uri, lookup, visited=visited | {uri}, depth=depth + 1
            )
            return [*parent_layers, layer]

        return [layer]


# ------------------------------------------------------------------
# Cross-source URI validation (standalone utility)
# ------------------------------------------------------------------


def validate_step_sources(steps: list[dict[str, Any]]) -> list[str]:
    """Validate URI prefixes on capability step ``skill_ref`` fields.

    Returns a list of warnings (e.g. for ``corp://`` refs that are not
    resolvable in a public context).

    Raises :class:`ValueError` for steps missing a valid URI prefix.
    """
    warnings: list[str] = []

    for idx, step in enumerate(steps):
        ref: str = step.get("skill_ref", "")
        if "://" not in ref:
            raise ValueError(
                f"Step {idx} skill_ref {ref!r} is missing a URI scheme prefix "
                f"(expected loom:// or corp://)"
            )

        scheme = ref.split("://", 1)[0].lower()
        if scheme not in VALID_URI_SCHEMES:
            raise ValueError(
                f"Step {idx} skill_ref {ref!r} has unsupported URI scheme "
                f"'{scheme}'. Supported: {', '.join(sorted(VALID_URI_SCHEMES))}"
            )

        if scheme == "corp":
            slug = ref.split("://", 1)[1]
            warnings.append(
                f"Step {idx} references corp://{slug} which is not resolvable in a public context"
            )

    return warnings
