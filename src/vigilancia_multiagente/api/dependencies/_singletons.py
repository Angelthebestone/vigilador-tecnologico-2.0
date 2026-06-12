"""Singleton factories for expensive infrastructure objects (FR-016/017/018).

Uses @lru_cache to ensure only one instance of each expensive object
is created during the application lifecycle.
"""

from __future__ import annotations

from functools import lru_cache
from typing import cast

from vigilancia_multiagente.config.settings import get_settings
from vigilancia_multiagente.domain.ports.embedding_gateway import EmbeddingGateway
from vigilancia_multiagente.domain.ports.llm_client import LLMClient
from vigilancia_multiagente.domain.ports.prompt_loader import PromptLoader
from vigilancia_multiagente.domain.ports.reranker import Reranker
from vigilancia_multiagente.domain.ports.source_trust_store import SourceTrustStore
from vigilancia_multiagente.infra.db.connection import database
from vigilancia_multiagente.infra.embeddings.gemini_gateway import GeminiEmbeddingGateway
from vigilancia_multiagente.infra.llm.minimax_client import MiniMaxClient
from vigilancia_multiagente.infra.mcp.mcp_cache import MCPSmartCache
from vigilancia_multiagente.infra.mcp.provider_registry import MCPProviderRegistry
from vigilancia_multiagente.infra.persistence.source_trust_repository import (
    SourceTrustRepository,
)
from vigilancia_multiagente.infra.prompts.loader import FilesystemPromptLoader
from vigilancia_multiagente.infra.reranking.semantic_reranker import SemanticReranker


@lru_cache(maxsize=1)
def get_embedding_gateway() -> EmbeddingGateway:
    """Singleton embedding gateway."""
    return cast(EmbeddingGateway, GeminiEmbeddingGateway())


@lru_cache(maxsize=1)
def get_llm_client() -> LLMClient:
    """Singleton LLM client."""
    return cast(LLMClient, MiniMaxClient())


@lru_cache(maxsize=1)
def get_mcp_cache() -> MCPSmartCache:
    """Singleton MCP cache."""
    return MCPSmartCache()


@lru_cache(maxsize=1)
def get_prompt_loader() -> PromptLoader:
    """Singleton prompt loader."""
    return cast(PromptLoader, FilesystemPromptLoader())


@lru_cache(maxsize=1)
def get_reranker() -> Reranker:
    """Singleton reranker."""
    return cast(Reranker, SemanticReranker(get_embedding_gateway()))


@lru_cache(maxsize=1)
def get_source_trust_store() -> SourceTrustStore:
    """Singleton source trust store."""
    return cast(SourceTrustStore, SourceTrustRepository(database))


@lru_cache(maxsize=1)
def get_provider_registry() -> MCPProviderRegistry:
    """Singleton MCP provider registry."""
    from pathlib import Path

    settings = get_settings()
    registry = MCPProviderRegistry()
    project_root = Path(__file__).resolve().parents[4]
    manifest = project_root / "config/mcp-providers.yaml"
    if not manifest.exists():
        manifest = project_root / "src/vigilancia_multiagente/infra/mcp/mcp-providers.json"
    registry.load_manifest(manifest)
    registry.ensure_standard_providers(settings)
    return registry
