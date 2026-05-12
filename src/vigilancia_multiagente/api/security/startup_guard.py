from urllib.parse import urlparse

from vigilancia_multiagente.config.settings import Settings


def validate_settings(settings: Settings) -> None:
    if not settings.embedding_api_key:
        raise RuntimeError("VT_EMBEDDING_API_KEY is required")
    if settings.embedding_dimensions != 768:
        raise RuntimeError("VT_EMBEDDING_DIMENSIONS must be 768")
    if settings.minimax_base_url and urlparse(settings.minimax_base_url).scheme not in {"http", "https"}:
        raise RuntimeError("VT_MINIMAX_BASE_URL must use http or https")


def validate_external_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise RuntimeError(f"Disallowed external URL scheme: {parsed.scheme}")
    if not parsed.netloc:
        raise RuntimeError("External URL must include a host")


def validate_stdio_command(command: str) -> None:
    if any(marker in command for marker in ("|", ";", "&&", "||", "`")):
        raise RuntimeError("STDIO command contains disallowed shell control characters")

