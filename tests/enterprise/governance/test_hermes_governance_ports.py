"""T035 + T041 smoke tests for spec 021 F1 governance Hermes extraction.

Covers the 6 small files ported in the first wave:

* governance/path_security.py
* governance/url_safety.py
* governance/website_policy.py
* governance/approvals/interrupt.py
* governance/approvals/slash_confirm.py
* tooling/output_limits.py

Each file gets 3 tests (input valido / invalido / edge case) per spec FR-025.
The 5 heavier files (file_safety 453 LOC, redact 504, schema_sanitizer 445,
approval 1441, lazy_deps 616) are deferred to a dedicated modularization
task — they need real refactoring (the constitution's <=400 LOC preferencia
applies).
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# path_security
# ---------------------------------------------------------------------------


def test_path_security_valid_within_dir(tmp_path: Path) -> None:
    from vigilancia_multiagente.enterprise.governance.path_security import (
        validate_within_dir,
    )

    inner = tmp_path / "subdir"
    inner.mkdir()
    assert validate_within_dir(inner, tmp_path) is None


def test_path_security_blocks_traversal(tmp_path: Path) -> None:
    from vigilancia_multiagente.enterprise.governance.path_security import (
        validate_within_dir,
    )

    outside = tmp_path.parent
    err = validate_within_dir(outside, tmp_path)
    assert err is not None
    assert "escapes" in err.lower()


def test_path_security_traversal_component_detection() -> None:
    from vigilancia_multiagente.enterprise.governance.path_security import (
        has_traversal_component,
    )

    assert has_traversal_component("a/../b") is True
    assert has_traversal_component("a/b/c") is False


# ---------------------------------------------------------------------------
# url_safety
# ---------------------------------------------------------------------------


def test_url_safety_blocks_metadata_hostname() -> None:
    from vigilancia_multiagente.enterprise.governance.url_safety import (
        is_always_blocked_url,
    )

    assert is_always_blocked_url("http://metadata.google.internal/x") is True


def test_url_safety_blocks_aws_metadata_ip() -> None:
    from vigilancia_multiagente.enterprise.governance.url_safety import (
        is_always_blocked_url,
    )

    assert is_always_blocked_url("http://169.254.169.254/latest/meta-data/") is True


def test_url_safety_unsupported_scheme_blocked() -> None:
    from vigilancia_multiagente.enterprise.governance.url_safety import is_safe_url

    # file:// is not http/https — must be blocked
    assert is_safe_url("file:///etc/passwd") is False


# ---------------------------------------------------------------------------
# website_policy
# ---------------------------------------------------------------------------


def test_website_policy_default_allows_unknown_url(tmp_path: Path) -> None:
    """No config file => default policy disabled => no blocks."""
    from vigilancia_multiagente.enterprise.governance.website_policy import (
        check_website_access,
        invalidate_cache,
    )

    invalidate_cache()
    cfg = tmp_path / "absent.yaml"
    assert check_website_access("https://example.com/", config_path=cfg) is None


def test_website_policy_blocks_listed_domain(tmp_path: Path) -> None:
    """A user-managed blocklist with a matching domain must block the URL."""
    from vigilancia_multiagente.enterprise.governance.website_policy import (
        check_website_access,
        invalidate_cache,
    )

    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        "security:\n"
        "  website_blocklist:\n"
        "    enabled: true\n"
        "    domains:\n"
        "      - blocked.example.com\n",
        encoding="utf-8",
    )
    invalidate_cache()
    result = check_website_access(
        "https://blocked.example.com/page", config_path=cfg
    )
    assert result is not None
    assert result["host"] == "blocked.example.com"


def test_website_policy_invalid_yaml_raises_when_explicit_path(tmp_path: Path) -> None:
    """Tests pass an explicit path — error propagates per documented contract."""
    from vigilancia_multiagente.enterprise.governance.website_policy import (
        WebsitePolicyError,
        check_website_access,
        invalidate_cache,
    )

    cfg = tmp_path / "broken.yaml"
    cfg.write_text("security: { unbalanced", encoding="utf-8")
    invalidate_cache()
    with pytest.raises(WebsitePolicyError):
        check_website_access("https://example.com/", config_path=cfg)


# ---------------------------------------------------------------------------
# approvals/interrupt
# ---------------------------------------------------------------------------


def test_interrupt_default_not_set() -> None:
    from vigilancia_multiagente.enterprise.governance.approvals.interrupt import (
        is_interrupted,
        set_interrupt,
    )

    set_interrupt(False)  # ensure clean
    assert is_interrupted() is False


def test_interrupt_set_then_clear() -> None:
    from vigilancia_multiagente.enterprise.governance.approvals.interrupt import (
        is_interrupted,
        set_interrupt,
    )

    set_interrupt(True)
    assert is_interrupted() is True
    set_interrupt(False)
    assert is_interrupted() is False


def test_interrupt_proxy_is_set() -> None:
    """Backward-compat _interrupt_event proxy maps Event API onto per-thread state."""
    from vigilancia_multiagente.enterprise.governance.approvals.interrupt import (
        _interrupt_event,
        set_interrupt,
    )

    set_interrupt(False)
    assert _interrupt_event.is_set() is False
    _interrupt_event.set()
    assert _interrupt_event.is_set() is True
    _interrupt_event.clear()
    assert _interrupt_event.is_set() is False


# ---------------------------------------------------------------------------
# approvals/slash_confirm
# ---------------------------------------------------------------------------


def test_slash_confirm_register_and_get_pending() -> None:
    from vigilancia_multiagente.enterprise.governance.approvals import slash_confirm

    async def _handler(choice: str) -> str | None:
        return f"done:{choice}"

    slash_confirm.register("session-1", "cid-1", "/reload-mcp", _handler)
    pending = slash_confirm.get_pending("session-1")
    assert pending is not None
    assert pending["confirm_id"] == "cid-1"
    slash_confirm.clear("session-1")


def test_slash_confirm_resolve_runs_handler() -> None:
    from vigilancia_multiagente.enterprise.governance.approvals import slash_confirm

    async def _handler(choice: str) -> str | None:
        return f"done:{choice}"

    slash_confirm.register("session-2", "cid-2", "/reload-mcp", _handler)
    result = asyncio.get_event_loop().run_until_complete(
        slash_confirm.resolve("session-2", "cid-2", "once")
    )
    assert result == "done:once"


def test_slash_confirm_stale_confirm_id_returns_none() -> None:
    from vigilancia_multiagente.enterprise.governance.approvals import slash_confirm

    async def _handler(choice: str) -> str | None:
        return choice

    slash_confirm.register("session-3", "cid-A", "/reload-mcp", _handler)
    # Resolve with a different confirm_id => stale, must return None
    result = asyncio.get_event_loop().run_until_complete(
        slash_confirm.resolve("session-3", "cid-OTHER", "once")
    )
    assert result is None
    slash_confirm.clear("session-3")


# ---------------------------------------------------------------------------
# tooling/output_limits
# ---------------------------------------------------------------------------


def test_output_limits_defaults() -> None:
    from vigilancia_multiagente.enterprise.tooling.output_limits import (
        DEFAULT_MAX_BYTES,
        DEFAULT_MAX_LINE_LENGTH,
        DEFAULT_MAX_LINES,
        get_tool_output_limits,
    )

    limits = get_tool_output_limits()
    assert limits["max_bytes"] == DEFAULT_MAX_BYTES
    assert limits["max_lines"] == DEFAULT_MAX_LINES
    assert limits["max_line_length"] == DEFAULT_MAX_LINE_LENGTH


def test_output_limits_shortcut_helpers_match() -> None:
    from vigilancia_multiagente.enterprise.tooling.output_limits import (
        get_max_bytes,
        get_max_line_length,
        get_max_lines,
        get_tool_output_limits,
    )

    full = get_tool_output_limits()
    assert get_max_bytes() == full["max_bytes"]
    assert get_max_lines() == full["max_lines"]
    assert get_max_line_length() == full["max_line_length"]


def test_output_limits_coerce_negative_falls_back() -> None:
    from vigilancia_multiagente.enterprise.tooling.output_limits import (
        DEFAULT_MAX_BYTES,
        _coerce_positive_int,
    )

    assert _coerce_positive_int(-5, DEFAULT_MAX_BYTES) == DEFAULT_MAX_BYTES
    assert _coerce_positive_int("not-a-number", DEFAULT_MAX_BYTES) == DEFAULT_MAX_BYTES
    assert _coerce_positive_int(100, DEFAULT_MAX_BYTES) == 100
