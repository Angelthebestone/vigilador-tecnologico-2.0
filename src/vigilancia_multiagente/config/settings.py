from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Vigilancia Tecnologica Multiagente"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    minimax_api_key: SecretStr | None = None
    minimax_model: str = "MiniMax-M2.7"
    minimax_base_url: str = "https://api.minimax.io"

    embedding_api_key: SecretStr | None = None
    embedding_model: str = "gemini-embedding-2"
    embedding_dimensions: int = 768
    embedding_batch_size: int = 16

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/vigilancia"

    mcp_default_timeout_ms: int = 30000
    mcp_default_retry_limit: int = 2

    # System Base (canonical global agent rules)
    system_base_version: str = "1.0.0"
    system_base_filename: str = "system-base.md"
    system_base_enabled: bool = True  # feature flag for rollback safety

    # Serper REST API (no MCP)
    serper_api_key: SecretStr | None = None

    # MiniMax Image MCP (Token Plan — separate key from text chat)
    minimax_image_api_key: SecretStr | None = None
    minimax_api_host: str = "https://api.minimax.io"

    # Playwright MCP
    playwright_headless: bool = True

    # Markitdown MCP
    markitdown_timeout: int = 60000

    # Sandbox
    sandbox_timeout: int = 120
    sandbox_max_output_size: int = 1_048_576  # 1MB

    # MCP Provider API Keys (all optional — system falls back gracefully)
    tavily_api_key: SecretStr | None = None
    exa_api_key: SecretStr | None = None
    jina_api_key: SecretStr | None = None
    brave_api_key: SecretStr | None = None
    firecrawl_api_key: SecretStr | None = None

    model_config = SettingsConfigDict(
        env_prefix="VT_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
