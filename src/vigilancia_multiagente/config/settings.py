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

    # Audit mode: enable detailed logging of data transformation between layers
    audit_mode: bool = False

    # MCP Provider API Keys (all optional — system falls back gracefully)
    tavily_api_key: SecretStr | None = None
    exa_api_key: SecretStr | None = None
    jina_api_key: SecretStr | None = None
    brave_api_key: SecretStr | None = None
    firecrawl_api_key: SecretStr | None = None
    cohere_api_key: SecretStr | None = None  # reranker; opcional, fallback a embeddings

    # OpenAlex: email para el "polite pool" (mejores rate limits) y API key
    # premium opcional. Usados tanto por el cliente REST como por el MCP.
    openalex_email: str | None = None
    openalex_api_key: SecretStr | None = None

    # Spec 007 - Sistema de Evaluacion Inteligente (Workstreams A..E).
    # Flags opt-in: default false preserva el comportamiento actual del
    # vigilador. Cada workstream se activa explicitamente sin afectar los
    # demas. Los adapters externos degradan a None si su clave no esta
    # configurada (Manejo de Errores Estricto + Convencion sobre Configuracion).
    eval_ws_a_enabled: bool = False  # Source Quality
    eval_ws_b_enabled: bool = False  # Data Intelligence
    eval_ws_c_enabled: bool = False  # Deep Analysis
    eval_ws_d_enabled: bool = False  # Strategic Signals
    eval_ws_e_enabled: bool = False  # Output Assurance

    google_factcheck_api_key: SecretStr | None = None
    retraction_watch_csv_url: str | None = None

    model_config = SettingsConfigDict(
        env_prefix="VT_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
