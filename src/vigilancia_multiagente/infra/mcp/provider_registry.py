from dataclasses import dataclass, field
from pathlib import Path
import json
from enum import StrEnum

from vigilancia_multiagente.config.settings import Settings
from vigilancia_multiagente.api.security.startup_guard import validate_external_url, validate_stdio_command


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
    enabled_tools: tuple[str, ...] = ()
    capabilities: tuple[str, ...] = ()
    headers: dict[str, str] = field(default_factory=dict)


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
            self.register(_provider_from_manifest(item))

    def ensure_standard_providers(self, settings: Settings) -> None:
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
            ),
            "brave": MCPProviderConfig(
                name="brave",
                transport=MCPTransport.STDIO,
                base_url_or_command="npx",
                auth_mode=MCPAuthMode.API_KEY,
                timeout_ms=settings.mcp_default_timeout_ms,
                retry_policy=RetryPolicy(max_attempts=settings.mcp_default_retry_limit, backoff_ms=500),
                enabled_tools=("brave_web_search", "brave_news_search"),
                capabilities=("search", "news"),
            ),
            "firecrawl": MCPProviderConfig(
                name="firecrawl",
                transport=MCPTransport.STDIO,
                base_url_or_command="npx",
                auth_mode=MCPAuthMode.API_KEY,
                timeout_ms=35000,
                retry_policy=RetryPolicy(max_attempts=1, backoff_ms=500),
                enabled_tools=("firecrawl_scrape",),
                capabilities=("scrape",),
            ),
            "google_scholar": MCPProviderConfig(
                name="google_scholar",
                transport=MCPTransport.STDIO,
                base_url_or_command="python",
                auth_mode=MCPAuthMode.NONE,
                timeout_ms=settings.mcp_default_timeout_ms,
                retry_policy=RetryPolicy(max_attempts=settings.mcp_default_retry_limit, backoff_ms=500),
                enabled_tools=("search_google_scholar_key_words", "search_google_scholar_advanced"),
                capabilities=("scholar",),
            ),
            "arxiv": MCPProviderConfig(
                name="arxiv",
                transport=MCPTransport.STDIO,
                base_url_or_command="python",
                auth_mode=MCPAuthMode.NONE,
                timeout_ms=settings.mcp_default_timeout_ms,
                retry_policy=RetryPolicy(max_attempts=settings.mcp_default_retry_limit, backoff_ms=500),
                enabled_tools=("search_papers", "download_paper", "read_paper"),
                capabilities=("papers",),
            ),
        }
        for name, provider in defaults.items():
            self._providers.setdefault(name, provider)

    def validate_ready(self, required_tools: tuple[str, ...]) -> None:
        missing_tools = [tool_name for tool_name in required_tools if not self.providers_for_tool(tool_name)]
        if missing_tools:
            raise RuntimeError(f"Missing MCP providers for tools: {', '.join(sorted(missing_tools))}")


def _provider_from_manifest(item: dict[str, object]) -> MCPProviderConfig:
    transport = MCPTransport(str(item["transport"]))
    auth_mode = MCPAuthMode(str(item.get("auth_mode", "NONE")))
    retry_payload = item.get("retry_policy") or {}
    if not isinstance(retry_payload, dict):
        raise TypeError("retry_policy must be an object")
    headers = item.get("headers") or {}
    if not isinstance(headers, dict):
        raise TypeError("headers must be an object")
    provider = MCPProviderConfig(
        name=str(item["name"]),
        transport=transport,
        base_url_or_command=str(item["base_url_or_command"]),
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
    if provider.transport == MCPTransport.STDIO:
        validate_stdio_command(provider.base_url_or_command)
    else:
        validate_external_url(provider.base_url_or_command)
    return provider

