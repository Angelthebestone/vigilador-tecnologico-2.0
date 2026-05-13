from urllib.parse import urlparse

from vigilancia_multiagente.config.settings import Settings


def validate_external_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise RuntimeError(f"Disallowed external URL scheme: {parsed.scheme}")
    if not parsed.netloc:
        raise RuntimeError("External URL must include a host")


def validate_stdio_command(command: str) -> None:
    if any(marker in command for marker in ("|", ";", "&&", "||", "`")):
        raise RuntimeError("STDIO command contains disallowed shell control characters")

