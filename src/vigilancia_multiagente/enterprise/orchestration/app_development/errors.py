# ROADMAP F5b - fuera de MVP 021; no registrar en runtime
"""Explicit error types for the app-development playbook."""

from __future__ import annotations


class AppDevError(Exception):
    """Base error for app-development playbook."""

    def __init__(self, phase: str, detail: str) -> None:
        self.phase = phase
        self.detail = detail
        super().__init__(f"[{phase}] {detail}")


class ApprovalDeniedError(AppDevError):
    """Raised when a gate approval is denied."""

    def __init__(self, phase: str) -> None:
        super().__init__(phase, "approval denied by user")


class InconsistencyBlockError(AppDevError):
    """Raised when analyze detects critical inconsistencies."""

    def __init__(self, inconsistencies: list[str]) -> None:
        self.inconsistencies = inconsistencies
        super().__init__("analyze", f"critical inconsistencies: {inconsistencies}")


class SandboxExecutionError(AppDevError):
    """Raised when sandbox execution fails after retries."""

    def __init__(self, phase: str, detail: str, attempts: int) -> None:
        self.attempts = attempts
        super().__init__(phase, f"sandbox failed after {attempts} attempts: {detail}")


class GuardrailViolationError(AppDevError):
    """Raised when a guardrail limit is exceeded."""

    def __init__(self, guardrail: str, value: int, limit: int) -> None:
        self.guardrail = guardrail
        self.value = value
        self.limit = limit
        super().__init__(
            "guardrails",
            f"guardrail '{guardrail}' violated: reached {value}, limit is {limit}",
        )


class RoutingRedirectError(AppDevError):
    """Raised when complexity routing redirects to another playbook."""

    def __init__(self, target_playbook: str) -> None:
        self.target_playbook = target_playbook
        super().__init__("routing", f"redirecting to playbook '{target_playbook}'")


class DirectoryNotWritableError(AppDevError):
    """Raised when target directory is not writable."""

    def __init__(self, path: str) -> None:
        self.path = path
        super().__init__("copy_final", f"directory not writable or missing: {path}")
