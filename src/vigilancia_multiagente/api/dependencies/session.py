"""Session services — DB connection, repositories, MCP clients, embeddings, LLM, vector index."""
from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from vigilancia_multiagente.config.settings import get_settings
from vigilancia_multiagente.domain.ports.embedding_gateway import EmbeddingGateway
from vigilancia_multiagente.domain.ports.llm_client import LLMClient
from vigilancia_multiagente.domain.ports.markitdown_port import MarkitdownPort
from vigilancia_multiagente.domain.ports.scholarly_works_gateway import ScholarlyWorksGateway
from vigilancia_multiagente.domain.ports.tool_executor import ToolExecutor
from vigilancia_multiagente.domain.ports.vector_index import VectorIndex
from vigilancia_multiagente.infra.db.connection import database
from vigilancia_multiagente.infra.mcp.execution_client import MCPExecutionClient
from vigilancia_multiagente.infra.persistence.postgres_repositories import (
    PostgresBranchResultRepository,
    PostgresPlanRepository,
    PostgresReportRepository,
    PostgresSessionRepository,
)
from vigilancia_multiagente.infra.persistence.vector_index import PostgresVectorIndex
from vigilancia_multiagente.infra.openalex.openalex_client import (
    OpenAlexScholarlyWorksGateway,
)

from ._singletons import (
    get_embedding_gateway,
    get_llm_client,
    get_mcp_cache,
    get_prompt_loader,
    get_provider_registry,
    get_reranker,
)

settings = get_settings()
PROJECT_ROOT = Path(__file__).resolve().parents[4]


def build_session_services() -> dict[str, Any]:
    """DB connection, repositories, MCP clients, embeddings, LLM, vector index."""
    srv: dict[str, Any] = {}
    srv["session_repository"] = PostgresSessionRepository(database)
    srv["plan_repository"] = PostgresPlanRepository(database)
    srv["branch_result_repository"] = PostgresBranchResultRepository(database)
    srv["report_repository"] = PostgresReportRepository(database)
    srv["vector_index"] = cast(VectorIndex, PostgresVectorIndex(database))
    srv["embedding_gateway"] = get_embedding_gateway()
    srv["llm_client"] = get_llm_client()
    srv["minimax_client"] = srv["llm_client"]
    mcp_cache = get_mcp_cache()
    srv["mcp_cache"] = mcp_cache
    srv["execution_client"] = cast(ToolExecutor, MCPExecutionClient(mcp_cache=mcp_cache))
    srv["markitdown_execution_client"] = MCPExecutionClient(mcp_cache=mcp_cache)
    srv["playwright_execution_client"] = MCPExecutionClient(mcp_cache=mcp_cache)
    provider_registry = get_provider_registry()
    provider_registry.validate_ready(
        (
            "tavily_search", "tavily_extract", "web_search_exa",
            "web_search_advanced_exa", "read_url", "guess_datetime_url",
            "brave_web_search", "brave_news_search", "firecrawl_scrape",
            "search_google_scholar_key_words", "search_papers", "fetch",
            "execute_code", "list_libraries", "visualize", "convert_to_markdown",
            "browser_navigate", "browser_snapshot", "browser_screenshot",
            "browser_click", "browser_type", "browser_select_option",
            "browser_hover", "browser_tabs", "browser_network_requests",
            "browser_network_request", "understand_image",
        )
    )
    srv["provider_registry"] = provider_registry
    srv["prompt_loader"] = get_prompt_loader()
    srv["scholarly_works_gateway"] = cast(
        ScholarlyWorksGateway, OpenAlexScholarlyWorksGateway()
    )
    srv["reranker"] = get_reranker()
    srv["settings"] = settings
    srv["database"] = database
    srv["PROJECT_ROOT"] = PROJECT_ROOT
    return srv
