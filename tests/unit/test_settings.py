import os

from loom.settings import LoomSettings


def test_settings_loads_defaults():
    """Settings should load from loom.yaml with sensible defaults."""
    # Clear any CI env overrides so we test the actual yaml defaults
    env_keys = ["LOOM_DATABASE__URL", "LOOM_DATABASE__PORT"]
    backup = {k: os.environ.pop(k) for k in env_keys if k in os.environ}
    try:
        settings = LoomSettings()
        assert settings.database.port == 5434
        assert settings.database.url == "postgresql+asyncpg://loom:loom@localhost:5434/loom"
    finally:
        os.environ.update(backup)
    assert settings.embedding.model == "openai/text-embedding-3-small"
    assert settings.embedding.dimensions == 1536
    assert settings.llm.provider == "openrouter"
    assert settings.llm.model == "google/gemini-3-flash-preview"
    assert settings.api.port == 8000


def test_settings_env_override():
    """Environment variables should override YAML values."""
    os.environ["LOOM_API__PORT"] = "9999"
    try:
        settings = LoomSettings()
        assert settings.api.port == 9999
    finally:
        del os.environ["LOOM_API__PORT"]
