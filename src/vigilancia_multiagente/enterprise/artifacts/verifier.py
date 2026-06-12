# ROADMAP F5b - fuera de MVP 021; no registrar en runtime
"""Verifier — validates artifact is functional in sandbox (FR-009, SC-003)."""

from __future__ import annotations

from vigilancia_multiagente.enterprise.artifacts.ports import (
    BuildResult,
    SandboxPort,
    VerificationResult,
)


class Verifier:
    """Validates that a built artifact is functional before publication."""

    def __init__(self, sandbox: SandboxPort) -> None:
        self._sandbox = sandbox

    def verify(self, build_result: BuildResult) -> VerificationResult:
        """Verify that the built artifact works correctly.

        Args:
            build_result: The result from BuilderAgent.

        Returns:
            VerificationResult indicating pass/fail with details.
        """
        if not build_result.success:
            return VerificationResult(
                passed=False,
                details=f"Artefacto no construido exitosamente: {build_result.error}",
            )

        verification_code = self._build_verification_code(build_result)
        sandbox_result = self._sandbox.execute(verification_code, build_result.artifact_type)

        if sandbox_result.success:
            return VerificationResult(
                passed=True,
                details=f"Artefacto '{build_result.artifact_type}' verificado correctamente.",
            )

        return VerificationResult(
            passed=False,
            details=(
                f"Verificación falló para '{build_result.artifact_type}': {sandbox_result.error}"
            ),
        )

    def _build_verification_code(self, build_result: BuildResult) -> str:
        return (
            f"# Verify {build_result.artifact_type}\n"
            f"# Path: {build_result.artifact_path}\n"
            f"assert_renders('{build_result.artifact_path}')\n"
        )
