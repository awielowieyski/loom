"""Unit tests for ExtendsResolver."""

import pytest

from loom.extends.resolver import ExtendsResolver, LayerInfo, ResolvedChain


@pytest.fixture
def resolver() -> ExtendsResolver:
    return ExtendsResolver()


class TestMergeLayers:
    def test_single_layer_no_header(self, resolver: ExtendsResolver) -> None:
        """A single layer should produce the content unchanged with no header."""
        layers = [
            {"source": "loom", "slug": "my-skill", "version": "1.0.0", "content": "Base content."}
        ]
        result = resolver.merge_layers(layers)
        assert isinstance(result, ResolvedChain)
        assert result.merged_content == "Base content."
        assert len(result.layers) == 1
        assert result.layers[0].slug == "my-skill"
        assert result.layers[0].version == "1.0.0"

    def test_two_layer_merge_corp(self, resolver: ExtendsResolver) -> None:
        """A corp layer appended to a base should include the Corporate Context header."""
        layers = [
            {
                "source": "loom",
                "slug": "base-skill",
                "version": "1.0.0",
                "content": "Base instructions.",
            },
            {
                "source": "corp",
                "slug": "corp-override",
                "version": "2.0.0",
                "content": "Corporate additions.",
            },
        ]
        result = resolver.merge_layers(layers)
        assert "Base instructions." in result.merged_content
        assert "## Corporate Context" in result.merged_content
        assert "Corporate additions." in result.merged_content
        assert len(result.layers) == 2

    def test_three_layer_merge(self, resolver: ExtendsResolver) -> None:
        """Three layers: base + corp + local, each with correct delimiter."""
        layers = [
            {"source": "loom", "slug": "base", "version": "1.0.0", "content": "Base."},
            {"source": "corp", "slug": "corp", "version": "1.0.0", "content": "Corp."},
            {"source": "local", "slug": "local", "version": None, "content": "Local."},
        ]
        result = resolver.merge_layers(layers)
        assert "Base." in result.merged_content
        assert "## Corporate Context" in result.merged_content
        assert "Corp." in result.merged_content
        assert "## Local Overrides" in result.merged_content
        assert "Local." in result.merged_content
        assert len(result.layers) == 3

    def test_layer_order_preserved(self, resolver: ExtendsResolver) -> None:
        """Content should appear in layer order."""
        layers = [
            {"source": "loom", "slug": "a", "content": "AAA"},
            {"source": "corp", "slug": "b", "content": "BBB"},
        ]
        result = resolver.merge_layers(layers)
        aaa_pos = result.merged_content.index("AAA")
        bbb_pos = result.merged_content.index("BBB")
        assert aaa_pos < bbb_pos

    def test_layer_info_populated(self, resolver: ExtendsResolver) -> None:
        """Each LayerInfo should carry correct metadata."""
        layers = [{"source": "loom", "slug": "s1", "version": "1.0.0", "content": "c1"}]
        result = resolver.merge_layers(layers)
        li = result.layers[0]
        assert isinstance(li, LayerInfo)
        assert li.source == "loom"
        assert li.slug == "s1"
        assert li.version == "1.0.0"
        assert li.content == "c1"


class TestParseExtendsUri:
    def test_loom_uri_with_version(self, resolver: ExtendsResolver) -> None:
        source, slug, version = resolver.parse_extends_uri("loom://my-skill@1.0.0")
        assert source == "loom"
        assert slug == "my-skill"
        assert version == "1.0.0"

    def test_corp_uri_with_version(self, resolver: ExtendsResolver) -> None:
        source, slug, version = resolver.parse_extends_uri("corp://corp-skill@2.5.1")
        assert source == "corp"
        assert slug == "corp-skill"
        assert version == "2.5.1"

    def test_uri_without_version(self, resolver: ExtendsResolver) -> None:
        source, slug, version = resolver.parse_extends_uri("loom://no-version-skill")
        assert source == "loom"
        assert slug == "no-version-skill"
        assert version is None

    def test_invalid_uri_missing_scheme(self, resolver: ExtendsResolver) -> None:
        with pytest.raises(ValueError, match="scheme"):
            resolver.parse_extends_uri("my-skill@1.0.0")

    def test_invalid_uri_empty_slug(self, resolver: ExtendsResolver) -> None:
        with pytest.raises(ValueError, match="slug"):
            resolver.parse_extends_uri("loom://@1.0.0")
