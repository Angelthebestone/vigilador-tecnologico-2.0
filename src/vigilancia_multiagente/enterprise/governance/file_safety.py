"""Shared file safety rules for write/read denial.

Adapted from Hermes Agent — Original file: ``agent/file_safety.py``
License: MIT (see ``documentation/hermes agent/hermes-agent/LICENSE``).

Spec 021 FR-025/026: governance F1 from Hermes.

**Deviations from upstream** (constitucion #2 KISS, #5 cambios quirurgicos —
Vigilador port carries only what it actually uses):

* ``HERMES_HOME``/profile resolution → replaced with ``~/.vigilador``.
  Vigilador has a single credential dir; no profile system.
* The Hermes "cross-profile write guard" (~150 LOC of profile classification)
  is **dropped** — Vigilador does not have profiles, so the guard would be
  dead code and confusing.
* Hermes-specific control-plane files (``.anthropic_oauth.json``,
  ``webhook_subscriptions.json``, ``bws_cache.json``, ``mcp-tokens/``,
  ``pairing/``) → replaced with the Vigilador-equivalent set under
  ``~/.vigilador/``: ``credentials/`` (Fernet-encrypted OAuth) and
  ``audit/`` (JSONL).

Universal protections preserved verbatim: OS-level secret files
(``~/.ssh``, ``~/.aws``, ``~/.gnupg``, ``~/.kube``, ``/etc/sudoers``,
``/etc/passwd``, ``/etc/shadow``), project-local ``.env`` files, and the
``VT_WRITE_SAFE_ROOT`` opt-in jail.

This is **defense-in-depth, not a security boundary** — a tool with shell
access can still ``cat`` or ``rm`` these files. The denylist returns clear
errors to models that respect tool denials and surfaces an audit trail in
logs.
"""

from __future__ import annotations

import os
from pathlib import Path


def _vigilador_home_path() -> Path:
    """Resolve ``~/.vigilador`` as the Vigilador credential/audit root."""
    return Path(os.path.expanduser("~/.vigilador"))


# ---------------------------------------------------------------------------
# Write denial — exact files and directory prefixes
# ---------------------------------------------------------------------------


def build_write_denied_paths(home: str) -> set[str]:
    """Return exact sensitive paths that must never be written."""
    vigilador_home = _vigilador_home_path()
    return {
        os.path.realpath(p)
        for p in [
            os.path.join(home, ".ssh", "authorized_keys"),
            os.path.join(home, ".ssh", "id_rsa"),
            os.path.join(home, ".ssh", "id_ed25519"),
            os.path.join(home, ".ssh", "config"),
            os.path.join(home, ".bashrc"),
            os.path.join(home, ".zshrc"),
            os.path.join(home, ".profile"),
            os.path.join(home, ".bash_profile"),
            os.path.join(home, ".zprofile"),
            os.path.join(home, ".netrc"),
            os.path.join(home, ".pgpass"),
            os.path.join(home, ".npmrc"),
            os.path.join(home, ".pypirc"),
            os.path.join(home, ".git-credentials"),
            "/etc/sudoers",
            "/etc/passwd",
            "/etc/shadow",
            # Vigilador credential and audit roots — Fernet-encrypted OAuth
            # tokens and audit-trail JSONL respectively. The agent never
            # needs to write these directly; they're managed by oauth_manager
            # and audit_log.
            str(vigilador_home / ".env"),
            str(vigilador_home / "credentials"),
            str(vigilador_home / "audit"),
        ]
    }


def build_write_denied_prefixes(home: str) -> list[str]:
    """Return sensitive directory prefixes that must never be written."""
    vigilador_home = _vigilador_home_path()
    return [
        os.path.realpath(p) + os.sep
        for p in [
            os.path.join(home, ".ssh"),
            os.path.join(home, ".aws"),
            os.path.join(home, ".gnupg"),
            os.path.join(home, ".kube"),
            "/etc/sudoers.d",
            "/etc/systemd",
            os.path.join(home, ".docker"),
            os.path.join(home, ".azure"),
            os.path.join(home, ".config", "gh"),
            os.path.join(home, ".config", "gcloud"),
            # Vigilador credential and audit roots — anything under either
            # tree must not be tampered with by tools.
            str(vigilador_home / "credentials"),
            str(vigilador_home / "audit"),
        ]
    ]


def get_safe_write_root() -> str | None:
    """Return the resolved ``VT_WRITE_SAFE_ROOT`` path, or ``None`` if unset.

    Opt-in jail: when the env var is set to a directory, all writes outside
    that directory are denied (in addition to the universal denylist).
    """
    root = os.getenv("VT_WRITE_SAFE_ROOT", "")
    if not root:
        return None
    # Path resolution may fail when the env var points at a non-existent or
    # permission-denied path. Constitucion #4: transform with explicit
    # context — return None and let the caller treat it as "no jail".
    try:
        return os.path.realpath(os.path.expanduser(root))
    except (OSError, ValueError) as exc:
        # Logging here would create a circular import with logging-config in
        # downstream callers; the calling tool will surface the failure.
        _ = exc
        return None


def is_write_denied(path: str) -> bool:
    """Return True if the path is blocked by the denylist or safe root."""
    home = os.path.realpath(os.path.expanduser("~"))
    resolved = os.path.realpath(os.path.expanduser(str(path)))

    if resolved in build_write_denied_paths(home):
        return True
    for prefix in build_write_denied_prefixes(home):
        if resolved.startswith(prefix):
            return True

    safe_root = get_safe_write_root()
    return bool(
        safe_root
        and not (
            resolved == safe_root or resolved.startswith(safe_root + os.sep)
        )
    )


# ---------------------------------------------------------------------------
# Read block — secret-bearing files
# ---------------------------------------------------------------------------


# Common secret-bearing project-local environment file basenames.
_BLOCKED_PROJECT_ENV_BASENAMES: set[str] = {
    ".env",
    ".env.local",
    ".env.development",
    ".env.production",
    ".env.test",
    ".env.staging",
    ".envrc",
}


# Vigilador credential file names under ``~/.vigilador/`` that must not be
# read by tools. Provider tools consume these via internal channels
# (oauth_manager, settings).
_VIGILADOR_CREDENTIAL_FILES: tuple[str, ...] = (
    ".env",
)


def get_read_block_error(path: str) -> str | None:
    """Return an error message when a read targets a denied path.

    Two categories are blocked:

    * Vigilador credential and audit stores under ``~/.vigilador/`` (Fernet
      OAuth tokens, audit trail) — read via ``oauth_manager`` / ``audit_log``,
      never directly.
    * Project-local environment files (``.env``, ``.env.local``, ...) anywhere
      on disk — these routinely hold API keys and DB passwords; the
      ``.env.example`` is the documented-shape substitute.

    **This is NOT a security boundary.** A tool with shell access can
    bypass the read-block. The denial returns a clear error to models that
    respect tool denials and produces an audit-friendly log entry.

    Callers that resolve relative paths against a non-process cwd MUST
    pre-resolve and pass the absolute path string — this function's
    ``resolve()`` is anchored at the Python process cwd.
    """
    resolved = Path(path).expanduser().resolve()
    vigilador_home = _vigilador_home_path()

    # Vigilador credentials + audit dir prefix match — anything inside is
    # secret material.
    try:
        credentials_dir = (vigilador_home / "credentials").resolve()
    except (OSError, RuntimeError):
        credentials_dir = vigilador_home / "credentials"
    try:
        audit_dir = (vigilador_home / "audit").resolve()
    except (OSError, RuntimeError):
        audit_dir = vigilador_home / "audit"

    for protected, label in (
        (credentials_dir, "credential"),
        (audit_dir, "audit"),
    ):
        if resolved == protected:
            return (
                f"Access denied: {path} is the Vigilador {label} directory "
                "and cannot be read directly. (Defense-in-depth — not a "
                "security boundary; a shell tool can still bypass.)"
            )
        try:
            resolved.relative_to(protected)
        except ValueError:
            continue
        return (
            f"Access denied: {path} is a Vigilador {label} file "
            "and cannot be read directly. (Defense-in-depth — not a "
            "security boundary; a shell tool can still bypass.)"
        )

    # Vigilador top-level .env (when present) is treated like a project .env.
    for name in _VIGILADOR_CREDENTIAL_FILES:
        try:
            blocked = (vigilador_home / name).resolve()
        except (OSError, RuntimeError):
            continue
        if resolved == blocked:
            return (
                f"Access denied: {path} is the Vigilador credential store "
                "and cannot be read directly. (Defense-in-depth — not a "
                "security boundary; a shell tool can still bypass.)"
            )

    # Block common secret-bearing project-local .env files anywhere on disk.
    if resolved.name in _BLOCKED_PROJECT_ENV_BASENAMES:
        return (
            f"Access denied: {path} is a secret-bearing environment file "
            "and cannot be read to prevent credential leakage. "
            "If you need to check the file structure, read .env.example instead. "
            "(Defense-in-depth — not a security boundary; a shell tool can still bypass.)"
        )

    return None
