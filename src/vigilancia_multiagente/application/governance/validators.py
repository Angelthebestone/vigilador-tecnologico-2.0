"""Validators for system base and branch overlay integrity.

Ensures that:
1. Branch overlays do not redefine global rules from the system base.
2. Prompt composition produces complete and valid output.
"""

from __future__ import annotations

from vigilancia_multiagente.domain.system_base import BranchOverlay, SystemBase

# Fields that a BranchOverlay MUST NOT redefine (belong to SystemBase).
_FORBIDDEN_OVERLAY_KEYS: frozenset[str] = frozenset(
    {
        "tool_usage_policy",
        "safety_limits",
        "error_handling",
        "output_style",
        "embedding_config",
    }
)


class PromptValidationError(ValueError):
    """Raised when prompt validation fails."""


class PromptValidator:
    """Validates system base integrity and branch overlay compliance."""

    def validate_overlay(self, system_base: SystemBase, overlay: BranchOverlay) -> None:
        """Check that a branch overlay does not redefine global rules.

        Args:
            system_base: The canonical system base.
            overlay: The branch overlay to validate.

        Raises:
            PromptValidationError: If the overlay redefines any forbidden key.
        """
        errors: list[str] = []

        # Check for forbidden fields in overlay
        overlay_dict = _dataclass_to_dict(overlay)
        for key in _FORBIDDEN_OVERLAY_KEYS:
            if key in overlay_dict:
                errors.append(
                    f"Branch overlay '{overlay.branch_type.value}' defines '{key}', "
                    f"which belongs to the system base (system-base.md). "
                    f"Remove it from the overlay."
                )

        # Check for empty required fields
        if not overlay.objective:
            errors.append(f"Branch overlay '{overlay.branch_type.value}' has an empty 'objective'.")

        if errors:
            raise PromptValidationError("\n".join(errors))

    def validate_composition(
        self,
        system_base: SystemBase,
        overlay: BranchOverlay,
        user_query: str,
    ) -> None:
        """Validate that a composition is complete and valid.

        Args:
            system_base: The canonical system base.
            overlay: The branch overlay.
            user_query: The user query string.

        Raises:
            PromptValidationError: If composition would be incomplete.
        """
        errors: list[str] = []

        if not user_query or not user_query.strip():
            errors.append("User query is empty.")

        # Verify system base has required sections
        if not system_base.global_rules:
            errors.append("System base is missing global_rules.")
        if not system_base.safety_limits:
            errors.append("System base is missing safety_limits.")

        if errors:
            raise PromptValidationError("\n".join(errors))


def _dataclass_to_dict(obj: object) -> dict[str, object]:
    """Convert a dataclass instance to a plain dict."""
    if hasattr(obj, "__dataclass_fields__"):
        from dataclasses import fields

        return {f.name: getattr(obj, f.name) for f in fields(obj)}  # type: ignore[arg-type]
    return {}
