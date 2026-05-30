"""Smoke tests for the 3 borderline Hermes governance ports (spec 021 F1.G).

Covers file_safety (249 LOC), schema_sanitizer (439 LOC), and redact
(461 LOC). Each module gets 3 tests (input valido / invalido / edge case)
per spec FR-025.

The 2 heavy files (approval.py 1441, lazy_deps.py 616) require dedicated
modularization — see ``docs/f1g-deferred-modularization.md``.
"""

from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# file_safety
# ---------------------------------------------------------------------------


def test_file_safety_blocks_ssh_authorized_keys() -> None:
    from vigilancia_multiagente.enterprise.governance.file_safety import (
        is_write_denied,
    )

    home = os.path.expanduser("~")
    target = os.path.join(home, ".ssh", "authorized_keys")
    assert is_write_denied(target) is True


def test_file_safety_allows_write_inside_project(tmp_path: Path) -> None:
    """Writes to a project-local file (no jail set) are allowed."""
    from vigilancia_multiagente.enterprise.governance.file_safety import (
        is_write_denied,
    )

    target = tmp_path / "report.md"
    target.write_text("ok", encoding="utf-8")
    # tmp_path is outside the universal denylist and no VT_WRITE_SAFE_ROOT is set
    assert is_write_denied(str(target)) is False


def test_file_safety_blocks_project_env_read(tmp_path: Path) -> None:
    """Reading a project-local .env returns a defense-in-depth error."""
    from vigilancia_multiagente.enterprise.governance.file_safety import (
        get_read_block_error,
    )

    env_file = tmp_path / ".env"
    env_file.write_text("VT_FAKE=secret", encoding="utf-8")
    err = get_read_block_error(str(env_file))
    assert err is not None
    assert "secret-bearing environment file" in err


# ---------------------------------------------------------------------------
# schema_sanitizer
# ---------------------------------------------------------------------------


def test_schema_sanitizer_injects_properties_for_object_type() -> None:
    from vigilancia_multiagente.enterprise.tooling.schema_sanitizer import (
        sanitize_tool_schemas,
    )

    tools = [
        {
            "type": "function",
            "function": {
                "name": "noop",
                "parameters": {"type": "object"},  # missing properties
            },
        }
    ]
    out = sanitize_tool_schemas(tools)
    assert out[0]["function"]["parameters"]["type"] == "object"
    assert out[0]["function"]["parameters"]["properties"] == {}


def test_schema_sanitizer_collapses_nullable_anyof() -> None:
    from vigilancia_multiagente.enterprise.tooling.schema_sanitizer import (
        strip_nullable_unions,
    )

    schema = {"anyOf": [{"type": "string"}, {"type": "null"}], "default": None}
    out = strip_nullable_unions(schema)
    assert out["type"] == "string"
    assert out.get("nullable") is True


def test_schema_sanitizer_strip_pattern_format_recovery() -> None:
    """Reactive strip removes pattern/format keys from tool param schemas."""
    from vigilancia_multiagente.enterprise.tooling.schema_sanitizer import (
        strip_pattern_and_format,
    )

    tools = [
        {
            "type": "function",
            "function": {
                "name": "needs_recovery",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "email": {"type": "string", "format": "email"},
                        "code": {"type": "string", "pattern": r"\d{6}"},
                    },
                },
            },
        }
    ]
    out, stripped = strip_pattern_and_format(tools)
    props = out[0]["function"]["parameters"]["properties"]
    assert "format" not in props["email"]
    assert "pattern" not in props["code"]
    assert stripped == 2


# ---------------------------------------------------------------------------
# redact
# ---------------------------------------------------------------------------


def test_redact_masks_openai_api_key() -> None:
    from vigilancia_multiagente.enterprise.governance.redact import (
        redact_sensitive_text,
    )

    text = "calling provider with sk-proj-abcdefghijklmnopqrstuvwxyz1234"
    out = redact_sensitive_text(text, force=True)
    # Long keys keep first 6 + last 4 chars
    assert "sk-pro" in out
    assert "..." in out
    # Full secret no longer present
    assert "abcdefghijklmnopqrstuvwxyz1234" not in out


def test_redact_masks_authorization_bearer_header() -> None:
    from vigilancia_multiagente.enterprise.governance.redact import (
        redact_sensitive_text,
    )

    text = "Authorization: Bearer abcdefghijklmnopqrstuvwxyz123456"
    out = redact_sensitive_text(text, force=True)
    # The original token is masked, the bearer prefix preserved
    assert "Bearer " in out
    assert "abcdefghijklmnopqrstuvwxyz123456" not in out


def test_redact_passthrough_when_disabled_and_not_forced() -> None:
    """When VT_REDACT_SECRETS is off and force=False, raw text passes through."""
    from vigilancia_multiagente.enterprise.governance import redact as redact_module

    # Temporarily flip the module-level snapshot (it's read once at import).
    original = redact_module._REDACT_ENABLED
    try:
        redact_module._REDACT_ENABLED = False
        text = "sk-proj-abcdefghijklmnopqrstuvwxyz1234"
        out = redact_module.redact_sensitive_text(text, force=False)
        assert out == text
    finally:
        redact_module._REDACT_ENABLED = original


def test_redact_mask_secret_short_input_returns_placeholder() -> None:
    """Edge case: short tokens (<floor) get the placeholder."""
    from vigilancia_multiagente.enterprise.governance.redact import mask_secret

    assert mask_secret("short") == "***"
    assert mask_secret("") == ""
    assert mask_secret("", empty="(not set)") == "(not set)"
