import os

from loom.settings import LoomSettings


def test_settings_loads_defaults():
    """Settings should load from loom.yaml with sensible defaults."""
    settings = LoomSettings()
    assert settings.database.url == "postgresql+asyncpg://loom:loom@localhost:5432/loom"
    assert settings.embedding.model == "text-embedding-3-small"
    assert settings.embedding.dimensions == 1536
    assert settings.llm.provider == "openrouter"
    assert settings.llm.model == "google/gemini-3-flash"
    assert settings.api.port == 8000


def test_settings_env_override():
    """Environment variables should override YAML values."""
    os.environ["LOOM_API__PORT"] = "9999"
    try:
        settings = LoomSettings()
        assert settings.api.port == 9999
    finally:
        del os.environ["LOOM_API__PORT"]
