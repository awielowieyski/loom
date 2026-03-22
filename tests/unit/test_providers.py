"""Tests for embedding and LLM provider factories."""

from loom.providers.embeddings import create_embedder
from loom.providers.llm import create_llm_model
from loom.settings import EmbeddingConfig, LLMConfig


def test_create_embedder_returns_embedder():
    config = EmbeddingConfig(provider="openai", model="text-embedding-3-small", dimensions=1536)
    embedder = create_embedder(config)
    assert embedder is not None


def test_create_llm_model_openrouter():
    config = LLMConfig(provider="openrouter", model="google/gemini-3-flash")
    model = create_llm_model(config)
    assert model is not None
