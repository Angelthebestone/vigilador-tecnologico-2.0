"""Regex-based secret redaction for logs and tool output.

Adapted from Hermes Agent — Original file: ``agent/redact.py``
License: MIT (see ``documentation/hermes agent/hermes-agent/LICENSE``).

Spec 021 FR-025/026: governance F1 from Hermes.

**Cohesion justification (constitucion #2 KISS / AHA, doc 06 §1.1)**: this
module is **497 LOC** — 24 percent over the ≤400 LOC preferencia. Splitting
it into ``redact_patterns.py`` + ``redact.py`` would be cosmetic, not real
modularization: ``redact_sensitive_text`` consults every pattern directly,
the gating substrings are tightly coupled to the patterns, and the
ordering of redaction passes is deliberate. The patterns and the
redactor co-evolve; an artificial split would force ``import *`` and add
no real seam. The "preferencia" yields to single-concern cohesion here.

**Deviations from upstream**:

* ``HERMES_REDACT_SECRETS`` env var → ``VT_REDACT_SECRETS``.
* Docstring references to ``hermes config / status / dump`` removed
  (Vigilador has no equivalent CLI surfaces yet).
* Universal credential prefix patterns (OpenAI, GitHub, Slack, AWS, ...)
  preserved verbatim — they catch real-world tokens regardless of host.

Applies pattern matching to mask API keys, tokens, and credentials before
they reach log files, verbose output, or gateway logs. Short tokens
(< 18 chars) are fully masked. Longer tokens preserve the first 6 and
last 4 characters for debuggability.
"""

from __future__ import annotations

import logging
import os
import re

logger = logging.getLogger(__name__)

# Sensitive query-string parameter names (case-insensitive exact match).
_SENSITIVE_QUERY_PARAMS = frozenset(
    {
        "access_token",
        "refresh_token",
        "id_token",
        "token",
        "api_key",
        "apikey",
        "client_secret",
        "password",
        "auth",
        "jwt",
        "session",
        "secret",
        "key",
        "code",
        "signature",
        "x-amz-signature",
    }
)

# Sensitive form-urlencoded / JSON body key names (case-insensitive exact match).
_SENSITIVE_BODY_KEYS = frozenset(
    {
        "access_token",
        "refresh_token",
        "id_token",
        "token",
        "api_key",
        "apikey",
        "client_secret",
        "password",
        "auth",
        "jwt",
        "secret",
        "private_key",
        "authorization",
        "key",
    }
)

# Snapshot at import time so runtime env mutations cannot disable redaction
# mid-session. ON by default — secure default. Opt-out via VT_REDACT_SECRETS=false.
_REDACT_ENABLED = os.getenv("VT_REDACT_SECRETS", "true").lower() in {
    "1",
    "true",
    "yes",
    "on",
}

# Known API key prefixes — match the prefix + contiguous token chars.
_PREFIX_PATTERNS = [
    r"sk-[A-Za-z0-9_-]{10,}",  # OpenAI / OpenRouter / Anthropic (sk-ant-*)
    r"ghp_[A-Za-z0-9]{10,}",  # GitHub PAT (classic)
    r"github_pat_[A-Za-z0-9_]{10,}",  # GitHub PAT (fine-grained)
    r"gho_[A-Za-z0-9]{10,}",  # GitHub OAuth access token
    r"ghu_[A-Za-z0-9]{10,}",  # GitHub user-to-server token
    r"ghs_[A-Za-z0-9]{10,}",  # GitHub server-to-server token
    r"ghr_[A-Za-z0-9]{10,}",  # GitHub refresh token
    r"xox[baprs]-[A-Za-z0-9-]{10,}",  # Slack tokens
    r"AIza[A-Za-z0-9_-]{30,}",  # Google API keys
    r"pplx-[A-Za-z0-9]{10,}",  # Perplexity
    r"fal_[A-Za-z0-9_-]{10,}",  # Fal.ai
    r"fc-[A-Za-z0-9]{10,}",  # Firecrawl
    r"bb_live_[A-Za-z0-9_-]{10,}",  # BrowserBase
    r"gAAAA[A-Za-z0-9_=-]{20,}",  # Codex encrypted tokens
    r"AKIA[A-Z0-9]{16}",  # AWS Access Key ID
    r"sk_live_[A-Za-z0-9]{10,}",  # Stripe secret key (live)
    r"sk_test_[A-Za-z0-9]{10,}",  # Stripe secret key (test)
    r"rk_live_[A-Za-z0-9]{10,}",  # Stripe restricted key
    r"SG\.[A-Za-z0-9_-]{10,}",  # SendGrid API key
    r"hf_[A-Za-z0-9]{10,}",  # HuggingFace token
    r"r8_[A-Za-z0-9]{10,}",  # Replicate API token
    r"npm_[A-Za-z0-9]{10,}",  # npm access token
    r"pypi-[A-Za-z0-9_-]{10,}",  # PyPI API token
    r"dop_v1_[A-Za-z0-9]{10,}",  # DigitalOcean PAT
    r"doo_v1_[A-Za-z0-9]{10,}",  # DigitalOcean OAuth
    r"am_[A-Za-z0-9_-]{10,}",  # AgentMail API key
    r"sk_[A-Za-z0-9_]{10,}",  # ElevenLabs TTS key
    r"tvly-[A-Za-z0-9]{10,}",  # Tavily search API key
    r"exa_[A-Za-z0-9]{10,}",  # Exa search API key
    r"gsk_[A-Za-z0-9]{10,}",  # Groq Cloud API key
    r"syt_[A-Za-z0-9]{10,}",  # Matrix access token
    r"retaindb_[A-Za-z0-9]{10,}",  # RetainDB API key
    r"hsk-[A-Za-z0-9]{10,}",  # Hindsight API key
    r"mem0_[A-Za-z0-9]{10,}",  # Mem0 Platform API key
    r"brv_[A-Za-z0-9]{10,}",  # ByteRover API key
    r"xai-[A-Za-z0-9]{30,}",  # xAI (Grok) API key
]

# ENV assignment patterns: KEY=value where KEY contains a secret-like name.
_SECRET_ENV_NAMES = r"(?:API_?KEY|TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIAL|AUTH)"
_ENV_ASSIGN_RE = re.compile(
    rf"([A-Z0-9_]{{0,50}}{_SECRET_ENV_NAMES}[A-Z0-9_]{{0,50}})\s*=\s*(['\"]?)(\S+)\2",
)

# JSON field patterns.
_JSON_KEY_NAMES = (
    r"(?:api_?[Kk]ey|token|secret|password|access_token|refresh_token|"
    r"auth_token|bearer|secret_value|raw_secret|secret_input|key_material)"
)
_JSON_FIELD_RE = re.compile(
    rf'("{_JSON_KEY_NAMES}")\s*:\s*"([^"]+)"',
    re.IGNORECASE,
)

# Authorization headers
_AUTH_HEADER_RE = re.compile(
    r"(Authorization:\s*Bearer\s+)(\S+)",
    re.IGNORECASE,
)

# Telegram bot tokens.
_TELEGRAM_RE = re.compile(r"(bot)?(\d{8,}):([-A-Za-z0-9_]{30,})")

# Private key blocks.
_PRIVATE_KEY_RE = re.compile(
    r"-----BEGIN[A-Z ]*PRIVATE KEY-----[\s\S]*?-----END[A-Z ]*PRIVATE KEY-----"
)

# Database connection strings.
_DB_CONNSTR_RE = re.compile(
    r"((?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis|amqp)://[^:]+:)([^@]+)(@)",
    re.IGNORECASE,
)

# JWT tokens.
_JWT_RE = re.compile(
    r"eyJ[A-Za-z0-9_-]{10,}"
    r"(?:\.[A-Za-z0-9_=-]{4,}){0,2}"
)

# Discord user/role mentions.
_DISCORD_MENTION_RE = re.compile(r"<@!?(\d{17,20})>")

# E.164 phone numbers.
_SIGNAL_PHONE_RE = re.compile(r"(\+[1-9]\d{6,14})(?![A-Za-z0-9])")

# URLs containing query strings.
_URL_WITH_QUERY_RE = re.compile(
    r"(https?|wss?|ftp)://"
    r"([^\s/?#]+)"
    r"([^\s?#]*)"
    r"\?([^\s#]+)"
    r"(#\S*)?",
)

# URLs containing userinfo.
_URL_USERINFO_RE = re.compile(
    r"(https?|wss?|ftp)://([^/\s:@]+):([^/\s@]+)@",
)

# HTTP access-log request targets with query strings.
_HTTP_REQUEST_TARGET_QUERY_RE = re.compile(
    r"\b((?:GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS|TRACE|CONNECT)\s+[^ \t\r\n\"']*?)"
    r"\?([^ \t\r\n\"']+)",
    re.IGNORECASE,
)

# Form-urlencoded body detection (conservative: full-string k=v&k=v).
_FORM_BODY_RE = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_.-]*=[^&\s]*(?:&[A-Za-z_][A-Za-z0-9_.-]*=[^&\s]*)+$"
)

# Compile known prefix patterns into one alternation.
_PREFIX_RE = re.compile(r"(?<![A-Za-z0-9_-])(" + "|".join(_PREFIX_PATTERNS) + r")(?![A-Za-z0-9_-])")


def mask_secret(
    value: str,
    *,
    head: int = 4,
    tail: int = 4,
    floor: int = 12,
    placeholder: str = "***",
    empty: str = "",
) -> str:
    """Mask a secret for display, preserving ``head`` and ``tail`` characters.

    Examples:
        >>> mask_secret("sk-proj-abcdef1234567890")
        'sk-p...7890'
        >>> mask_secret("short")
        '***'
        >>> mask_secret("")
        ''
        >>> mask_secret("", empty="(not set)")
        '(not set)'
    """
    if not value:
        return empty
    if len(value) < floor:
        return placeholder
    return f"{value[:head]}...{value[-tail:]}"


def _mask_token(token: str) -> str:
    """Mask a log token — conservative 18-char floor, preserves 6 prefix / 4 suffix."""
    if not token:
        return "***"
    return mask_secret(token, head=6, tail=4, floor=18)


def _redact_query_string(query: str) -> str:
    """Redact sensitive parameter values in a URL query string."""
    if not query:
        return query
    parts = []
    for pair in query.split("&"):
        if "=" not in pair:
            parts.append(pair)
            continue
        key, _, _value = pair.partition("=")
        if key.lower() in _SENSITIVE_QUERY_PARAMS:
            parts.append(f"{key}=***")
        else:
            parts.append(pair)
    return "&".join(parts)


def _redact_url_query_params(text: str) -> str:
    """Scan text for URLs with query strings and redact sensitive params."""

    def _sub(m: re.Match) -> str:
        scheme = m.group(1)
        authority = m.group(2)
        path = m.group(3)
        query = _redact_query_string(m.group(4))
        fragment = m.group(5) or ""
        return f"{scheme}://{authority}{path}?{query}{fragment}"

    return _URL_WITH_QUERY_RE.sub(_sub, text)


def _redact_url_userinfo(text: str) -> str:
    """Strip ``user:password@`` from HTTP/WS/FTP URLs."""
    return _URL_USERINFO_RE.sub(
        lambda m: f"{m.group(1)}://{m.group(2)}:***@",
        text,
    )


def _redact_http_request_target_query_params(text: str) -> str:
    """Redact sensitive query params in HTTP access-log request targets."""

    def _sub(m: re.Match) -> str:
        prefix = m.group(1)
        query = _redact_query_string(m.group(2))
        return f"{prefix}?{query}"

    return _HTTP_REQUEST_TARGET_QUERY_RE.sub(_sub, text)


def _redact_form_body(text: str) -> str:
    """Redact sensitive values in a form-urlencoded body.

    Only applies when the entire input looks like a pure form body
    (k=v&k=v with no newlines, no other text).
    """
    if not text or "\n" in text or "&" not in text:
        return text
    if not _FORM_BODY_RE.match(text.strip()):
        return text
    return _redact_query_string(text.strip())


def redact_sensitive_text(
    text: str | None, *, force: bool = False, code_file: bool = False
) -> str | None:
    """Apply all redaction patterns to a block of text.

    Safe to call on any string — non-matching text passes through unchanged.
    Disabled by default — enable via ``VT_REDACT_SECRETS=true``. Set
    ``force=True`` for safety boundaries that must never return raw secrets.
    Set ``code_file=True`` to skip ENV-assignment and JSON-field patterns
    when the text is known to be source code (constants/fixtures).

    Performance: each regex pattern is gated behind a cheap substring
    pre-check (e.g. ``"=" in text`` for ENV assignments). On a typical log
    line (no secrets) this drops the 13-pattern scan from ~5.6us to ~1.8us
    per record (-68%). The pre-checks are conservative — false positives
    still run the full regex; false negatives are impossible because every
    regex requires the gated substring.
    """
    if text is None:
        return None
    if not isinstance(text, str):
        text = str(text)
    if not text:
        return text
    if not (force or _REDACT_ENABLED):
        return text

    # Known prefixes (sk-, ghp_, etc.).
    if _has_known_prefix_substring(text):
        text = _PREFIX_RE.sub(lambda m: _mask_token(m.group(1)), text)

    # ENV assignments (skip for code files).
    if not code_file:
        if "=" in text:

            def _redact_env(m):
                name, quote, value = m.group(1), m.group(2), m.group(3)
                return f"{name}={quote}{_mask_token(value)}{quote}"

            text = _ENV_ASSIGN_RE.sub(_redact_env, text)

        if ":" in text and '"' in text:

            def _redact_json(m):
                key, value = m.group(1), m.group(2)
                return f'{key}: "{_mask_token(value)}"'

            text = _JSON_FIELD_RE.sub(_redact_json, text)

    # Authorization headers.
    if "uthorization" in text or "UTHORIZATION" in text:
        text = _AUTH_HEADER_RE.sub(
            lambda m: m.group(1) + _mask_token(m.group(2)),
            text,
        )

    # Telegram bot tokens.
    if ":" in text:

        def _redact_telegram(m):
            prefix = m.group(1) or ""
            digits = m.group(2)
            return f"{prefix}{digits}:***"

        text = _TELEGRAM_RE.sub(_redact_telegram, text)

    # Private key blocks.
    if "BEGIN" in text and "-----" in text:
        text = _PRIVATE_KEY_RE.sub("[REDACTED PRIVATE KEY]", text)

    # Database connection string passwords.
    if "://" in text:
        text = _DB_CONNSTR_RE.sub(lambda m: f"{m.group(1)}***{m.group(3)}", text)

    # JWT tokens.
    if "eyJ" in text:
        text = _JWT_RE.sub(lambda m: _mask_token(m.group(0)), text)

    # NOTE: Web-URL redaction (query params + userinfo + HTTP access-log
    # request targets) is intentionally OFF. Many legitimate workflows pass
    # opaque tokens through query strings. Known credential shapes inside
    # URLs are still caught by _PREFIX_RE/_JWT_RE/_DB_CONNSTR_RE.

    # Form-urlencoded bodies.
    if "&" in text and "=" in text:
        text = _redact_form_body(text)

    # Discord mentions.
    if "<@" in text:
        text = _DISCORD_MENTION_RE.sub(lambda m: f"<@{'!' if '!' in m.group(0) else ''}***>", text)

    # E.164 phone numbers.
    if "+" in text:

        def _redact_phone(m):
            phone = m.group(1)
            if len(phone) <= 8:
                return phone[:2] + "****" + phone[-2:]
            return phone[:4] + "****" + phone[-4:]

        text = _SIGNAL_PHONE_RE.sub(_redact_phone, text)

    return text


def _extract_literal_prefix(pattern: str) -> str:
    """Return the leading literal characters of a regex pattern."""
    meta = "[(\\.?*+|{^$"
    for i, ch in enumerate(pattern):
        if ch in meta:
            return pattern[:i]
    return pattern


_PREFIX_SUBSTRINGS = tuple(_extract_literal_prefix(p) for p in _PREFIX_PATTERNS)


def _has_known_prefix_substring(text: str) -> bool:
    """Cheap pre-check before invoking the expensive ``_PREFIX_RE``."""
    return any(p in text for p in _PREFIX_SUBSTRINGS)


_HTTP_METHOD_SUBSTRINGS = (
    "GET ",
    "POST ",
    "PUT ",
    "PATCH ",
    "DELETE ",
    "HEAD ",
    "OPTIONS ",
    "TRACE ",
    "CONNECT ",
)


def _has_http_method_substring(text: str) -> bool:
    """Cheap pre-check before scanning for access-log request targets."""
    upper = text.upper()
    return any(method in upper for method in _HTTP_METHOD_SUBSTRINGS)


class RedactingFormatter(logging.Formatter):
    """Log formatter that redacts secrets from all log messages."""

    def __init__(self, fmt=None, datefmt=None, style="%", **kwargs):
        super().__init__(fmt, datefmt, style=style, **kwargs)  # type: ignore[arg-type]

    def format(self, record: logging.LogRecord) -> str:
        original = super().format(record)
        return redact_sensitive_text(original) or original
