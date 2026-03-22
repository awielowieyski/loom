"""Embedding provider factory."""

import os

from pydantic_ai import Embedder
from pydantic_ai.embeddings.openai import OpenAIEmbeddingModel
from pydantic_ai.providers.openai import OpenAIProvider

from loom.settings import EmbeddingConfig


def create_embedder(config: EmbeddingConfig) -> Embedder:
    """Create an Embedder from the given config."""
    if config.provider == "openai":
        api_key = os.environ.get("OPENAI_API_KEY", "")
        model = OpenAIEmbeddingModel(config.model, provider=OpenAIProvider(api_key=api_key))
        return Embedder(model)
    raise ValueError(f"Unsupported embedding provider: {config.provider}")
