import json
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from vigilancia_multiagente.config.settings import Settings

_MCP_SERVERS = Path(__file__).resolve().parents[4] / ".mcp-servers"



class MCPTransport(StrEnum):
    STDIO = "STDIO"
    HTTP = "HTTP"
    STREAMABLE_HTTP = "STREAMABLE_HTTP"


class MCPAuthMode(StrEnum):
    API_KEY = "API_KEY"
    BEARER = "BEARER"
    OAUTH = "OAUTH"
    NONE = "NONE"


@dataclass(slots=True)
class RetryPolicy:
    max_attempts: int
    backoff_ms: int


@dataclass(slots=True)
class MCPProviderConfig:
    name: str
    transport: MCPTransport
    base_url_or_command: str
    auth_mode: MCPAuthMode
    timeout_ms: int
    retry_policy: RetryPolicy
    arguments: list[str] = field(default_factory=list)
    enabled_tools: tuple[str, ...] = ()
    capabilities: tuple[str, ...] = ()
    headers: dict[str, str] = field(default_factory=dict)
    environment: dict[str, str] = field(default_factory=dict)


class MCPProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, MCPProviderConfig] = {}

    def register(self, provider: MCPProviderConfig) -> None:
        self._providers[provider.name] = provider

    def get(self, name: str) -> MCPProviderConfig:
        provider = self._providers.get(name)
        if provider is None:
            raise KeyError(f"Provider not registered: {name}")
        return provider

    def list(self) -> tuple[MCPProviderConfig, ...]:
        return tuple(self._providers.values())

    def providers_for_tool(self, tool_name: str) -> tuple[MCPProviderConfig, ...]:
        return tuple(provider for provider in self._providers.values() if tool_name in provider.enabled_tools)

    def provider_names_for_tools(self, tools: tuple[str, ...]) -> tuple[str, ...]:
        names: list[str] = []
        for tool_name in tools:
            names.extend(provider.name for provider in self.providers_for_tool(tool_name))
        return tuple(dict.fromkeys(names))

    def load_manifest(self, manifest_path: Path) -> None:
        if not manifest_path.exists():
            return
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        providers = payload.get("providers", payload)
        if not isinstance(providers, list):
            raise TypeError("MCP provider manifest must contain a provider list")
        for item in providers:
            if str(item.get("name")) == "serper":
                continue
            self.register(_provider_from_manifest(item))

    def ensure_standard_providers(self, settings: Settings) -> None:
        tavily_key = _secret(settings.tavily_api_key)
        exa_key = _secret(settings.exa_api_key)
        jina_key = _secret(settings.jina_api_key)
        brave_key = _secret(settings.brave_api_key)
        firecrawl_key = _secret(settings.firecrawl_api_key)
        defaults = {
            "tavily": MCPProviderConfig(
                name="tavily",
                transport=MCPTransport.HTTP,
                base_url_or_command="https://mcp.tavily.com/mcp",
                auth_mode=MCPAuthMode.API_KEY,
                timeout_ms=settings.mcp_default_timeout_ms,
                retry_policy=RetryPolicy(max_attempts=settings.mcp_default_retry_limit, backoff_ms=500),
                enabled_tools=("tavily_search", "tavily_extract"),
                capabilities=("search", "extract"),
                headers=_auth_headers(tavily_key, extra_name="X-API-Key"),
            ),
            "exa": MCPProviderConfig(
                name="exa",
                transport=MCPTransport.HTTP,
                base_url_or_command="https://mcp.exa.ai/mcp",
                auth_mode=MCPAuthMode.API_KEY,
                timeout_ms=settings.mcp_default_timeout_ms,
                retry_policy=RetryPolicy(max_attempts=settings.mcp_default_retry_limit, backoff_ms=500),
                enabled_tools=("web_search_exa", "web_fetch_exa", "web_search_advanced_exa"),
                capabilities=("search", "company"),
                headers=_auth_headers(exa_key, extra_name="x-api-key"),
            ),
            "jina": MCPProviderConfig(
                name="jina",
                transport=MCPTransport.HTTP,
                base_url_or_command="https://mcp.jina.ai/v1?include_tools=read_url,search_web,guess_datetime_url",
                auth_mode=MCPAuthMode.BEARER,
                timeout_ms=settings.mcp_default_timeout_ms,
                retry_policy=RetryPolicy(max_attempts=settings.mcp_default_retry_limit, backoff_ms=500),
                enabled_tools=("read_url", "search_web", "guess_datetime_url"),
                capabilities=("read", "search", "metadata"),
                headers=_auth_headers(jina_key),
            ),
            "brave": MCPProviderConfig(
                name="brave",
                transport=MCPTransport.STDIO,
                base_url_or_command="npx",
                arguments=["-y", "@brave/brave-search-mcp-server", "--transport", "stdio"],
                auth_mode=MCPAuthMode.API_KEY,
                timeout_ms=settings.mcp_default_timeout_ms,
                retry_policy=RetryPolicy(max_attempts=settings.mcp_default_retry_limit, backoff_ms=500),
                enabled_tools=("brave_web_search", "brave_news_search"),
                capabilities=("search", "news"),
                environment=_env("BRAVE_API_KEY", brave_key),
            ),
            "firecrawl": MCPProviderConfig(
                name="firecrawl",
                transport=MCPTransport.STDIO,
                base_url_or_command="npx",
                arguments=["-y", "firecrawl-mcp"],
                auth_mode=MCPAuthMode.API_KEY,
                timeout_ms=35000,
                retry_policy=RetryPolicy(max_attempts=1, backoff_ms=500),
                enabled_tools=("firecrawl_scrape",),
                capabilities=("scrape",),
                environment=_env("FIRECRAWL_API_KEY", firecrawl_key),
            ),
            "google_scholar": MCPProviderConfig(
                name="google_scholar",
                transport=MCPTransport.STDIO,
                base_url_or_command="python",
                arguments=["-u", str(_MCP_SERVERS / "google-scholar/Google-Scholar-MCP-Server-main/google_scholar_server.py")],
                auth_mode=MCPAuthMode.NONE,
                timeout_ms=settings.mcp_default_timeout_ms,
                retry_policy=RetryPolicy(max_attempts=settings.mcp_default_retry_limit, backoff_ms=500),
                enabled_tools=("search_google_scholar_key_words", "search_google_scholar_advanced", "get_author_info"),
                capabilities=("scholar",),
            ),
            "arxiv": MCPProviderConfig(
                name="arxiv",
                transport=MCPTransport.STDIO,
                base_url_or_command="python",
                arguments=["-m", "arxiv_mcp_server"],
                auth_mode=MCPAuthMode.NONE,
                timeout_ms=settings.mcp_default_timeout_ms,
                retry_policy=RetryPolicy(max_attempts=settings.mcp_default_retry_limit, backoff_ms=500),
                enabled_tools=("search_papers", "download_paper", "read_paper"),
                capabilities=("papers",),
            ),
            "fetch": MCPProviderConfig(
                name="fetch",
                transport=MCPTransport.STDIO,
                base_url_or_command="python",
                arguments=["-m", "mcp_server_fetch"],
                auth_mode=MCPAuthMode.NONE,
                timeout_ms=settings.mcp_default_timeout_ms,
                retry_policy=RetryPolicy(max_attempts=settings.mcp_default_retry_limit, backoff_ms=500),
                enabled_tools=("fetch",),
                capabilities=("fetch",),
            ),
        }
        for name, provider in defaults.items():
            current = self._providers.get(name)
            self._providers[name] = _merge_provider(current, provider) if current else provider

    def validate_ready(self, required_tools: tuple[str, ...]) -> None:
        missing_tools = [tool_name for tool_name in required_tools if not self.providers_for_tool(tool_name)]
        if missing_tools:
            raise RuntimeError(f"Missing MCP providers for tools: {', '.join(sorted(missing_tools))}")


def _provider_from_manifest(item: dict[str, object]) -> MCPProviderConfig:
    transport = MCPTransport(str(item["transport"]))
    auth_mode = MCPAuthMode(str(item.get("auth_mode", "NONE")))
    retry_payload = item.get("retry_policy") or {}
    headers = item.get("headers") or {}
    provider = MCPProviderConfig(
        name=str(item["name"]),
        transport=transport,
        base_url_or_command=str(item["base_url_or_command"]),
        arguments=list(item.get("arguments", [])),
        auth_mode=auth_mode,
        timeout_ms=int(item.get("timeout_ms", 30000)),
        retry_policy=RetryPolicy(
            max_attempts=int(retry_payload.get("max_attempts", 2)),
            backoff_ms=int(retry_payload.get("backoff_ms", 500)),
        ),
        enabled_tools=tuple(str(tool) for tool in item.get("enabled_tools", [])),
        capabilities=tuple(str(capability) for capability in item.get("capabilities", [])),
        headers={str(key): str(value) for key, value in headers.items()},
    )
    return provider


def _secret(value: object) -> str | None:
    if value is None:
        return None
    return value.get_secret_value() if hasattr(value, "get_secret_value") else str(value)


def _auth_headers(api_key: str | None, *, extra_name: str | None = None) -> dict[str, str]:
    if not api_key:
        return {}
    headers = {"Authorization": f"Bearer {api_key}"}
    if extra_name:
        headers[extra_name] = api_key
    return headers


def _env(name: str, value: str | None) -> dict[str, str]:
    return {name: value} if value else {}


def _merge_provider(current: MCPProviderConfig, default: MCPProviderConfig) -> MCPProviderConfig:
    headers = {**default.headers, **current.headers}
    environment = {**default.environment, **current.environment}
    return MCPProviderConfig(
        name=current.name,
        transport=current.transport,
        base_url_or_command=current.base_url_or_command,
        auth_mode=current.auth_mode,
        timeout_ms=current.timeout_ms,
        retry_policy=current.retry_policy,
        arguments=current.arguments,
        enabled_tools=current.enabled_tools,
        capabilities=current.capabilities,
        headers=headers,
        environment=environment,
    )

