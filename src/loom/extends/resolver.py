"""Client-side extends resolver for merging skill layers."""

from __future__ import annotations

from dataclasses import dataclass, field


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

        if "@" in rest:
            slug, version = rest.rsplit("@", 1)
        else:
            slug = rest
            version = None

        if not slug:
            raise ValueError(f"Invalid extends URI (empty slug): {uri!r}")

        return source, slug, version
