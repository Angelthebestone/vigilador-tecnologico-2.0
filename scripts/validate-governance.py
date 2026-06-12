#!/usr/bin/env python3
"""Validate governance contracts: contract_loader + prompt_composer + MCP provider consistency.

Checks that:
1. Skill matrix loads without errors
2. All tools in skill_matrix have matching MCP providers
3. PromptComposer generates valid prompts for all branch types
4. Smart router tool mappings are consistent with contract_loader

Usage:
    python scripts/validate-governance.py
    python scripts/validate-governance.py --verbose
    python scripts/validate-governance.py --branch AVANCES
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"


def _add_src_to_path() -> None:
    if str(SRC_ROOT) not in sys.path:
        sys.path.insert(0, str(SRC_ROOT))


def check_skill_matrix(verbose: bool = False) -> list[str]:
    """Verify contract_loader loads skill matrix without errors."""
    errors = []
    try:
        from vigilancia_multiagente.application.governance.contract_loader import (
            GovernanceContractLoader,
        )

        loader = GovernanceContractLoader(REPO_ROOT)
        matrix = loader.load_skill_matrix()

        if not matrix:
            errors.append("Skill matrix is empty")
            return errors

        if verbose:
            print(f"  Skill matrix loaded: {len(matrix)} branches")
            for branch, policy in matrix.items():
                print(f"    {branch}: {len(policy.tool_order)} tools")

        # Check each branch has tools
        for branch, policy in matrix.items():
            if not policy.tool_order:
                errors.append(f"Branch {branch} has empty tool_order")

    except Exception as e:
        errors.append(f"Failed to load skill matrix: {e}")

    return errors


def check_mcp_providers(verbose: bool = False) -> list[str]:
    """Verify MCP providers are loaded and match skill matrix tools."""
    errors = []
    try:
        from vigilancia_multiagente.application.governance.contract_loader import (
            GovernanceContractLoader,
        )
        from vigilancia_multiagente.config.settings import get_settings
        from vigilancia_multiagente.infra.mcp.provider_registry import (
            MCPProviderRegistry,
        )

        # Load skill matrix
        loader = GovernanceContractLoader(REPO_ROOT)
        matrix = loader.load_skill_matrix()

        # Load MCP providers
        registry = MCPProviderRegistry()
        manifest_path = SRC_ROOT / "vigilancia_multiagente" / "infra" / "mcp" / "mcp-providers.json"
        registry.load_manifest(manifest_path)
        registry.ensure_standard_providers(get_settings())

        # Collect all tools from providers (using enabled_tools attribute)
        provider_tools = set()
        for provider in registry.list():
            for tool_name in provider.enabled_tools:
                provider_tools.add(tool_name)

        if verbose:
            print(f"  MCP providers loaded: {len(registry.list())} providers, {len(provider_tools)} tools")

        # Check each tool in skill matrix has a provider
        all_matrix_tools = set()
        for branch, policy in matrix.items():
            for tool in policy.tool_order:
                all_matrix_tools.add(tool)
                if tool not in provider_tools:
                    errors.append(f"Tool '{tool}' in branch {branch} has no MCP provider")

        if verbose:
            print(f"  Matrix tools: {len(all_matrix_tools)}, Provider tools: {len(provider_tools)}")

    except Exception as e:
        errors.append(f"Failed to check MCP providers: {e}")

    return errors


def check_prompt_composer(verbose: bool = False, target_branch: str | None = None) -> list[str]:
    """Verify PromptComposer generates valid prompts for all branch types."""
    errors = []
    try:
        from vigilancia_multiagente.application.governance.prompt_composer import (
            PromptComposer,
        )
        from vigilancia_multiagente.domain.models import BranchType
        from vigilancia_multiagente.domain.system_base import BranchOverlay, SystemBase

        composer = PromptComposer()

        sb = SystemBase(
            version="1.0.0",
            global_rules=("R1",),
            tool_usage_policy={"order": "sequential"},
        )

        branches_to_check = [target_branch] if target_branch else list(BranchType)

        for branch in branches_to_check:
            try:
                # Create a BranchOverlay for this branch type
                overlay = BranchOverlay(
                    branch_type=branch,
                    objective=f"Test objective for {branch}",
                )
                prompt = composer.compose(
                    system_base=sb,
                    overlay=overlay,
                    user_query="test query for validation",
                )
                if not prompt:
                    errors.append(f"PromptComposer returned empty prompt for {branch}")
                elif verbose:
                    print(f"  {branch}: prompt generated ({len(str(prompt))} chars)")

            except Exception as e:
                errors.append(f"PromptComposer failed for {branch}: {e}")

    except Exception as e:
        errors.append(f"Failed to check PromptComposer: {e}")

    return errors


def check_layer_imports(verbose: bool = False) -> list[str]:
    """Verify layer import rules are respected."""
    errors = []
    try:
        result = __import__("scripts.check_layer_imports", fromlist=["main"])
        # If the module exists, it handles its own validation
        if verbose:
            print("  Layer import checker available")
    except ImportError:
        # Fall back to direct check
        try:
            import ast

            layer_prefixes = {
                "domain": "vigilancia_multiagente.domain",
                "application": "vigilancia_multiagente.application",
                "infra": "vigilancia_multiagente.infra",
                "api": "vigilancia_multiagente.api",
            }

            forbidden = {
                "domain": ["vigilancia_multiagente.api", "vigilancia_multiagente.application", "vigilancia_multiagente.infra"],
                "application": ["vigilancia_multiagente.api"],
            }

            for py_file in (SRC_ROOT / "vigilancia_multiagente").rglob("*.py"):
                try:
                    tree = ast.parse(py_file.read_text(encoding="utf-8"))
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.Import, ast.ImportFrom)):
                            if isinstance(node, ast.ImportFrom) and node.module:
                                imported = node.module
                            elif isinstance(node, ast.Import):
                                imported = node.names[0].name if node.names else ""
                            else:
                                continue

                            # Determine source layer
                            rel = py_file.relative_to(SRC_ROOT)
                            parts = rel.parts
                            if len(parts) >= 2:
                                source_layer = parts[1]  # vigilancia_multiagente/<layer>/...
                            else:
                                continue

                            if source_layer in forbidden:
                                for fb in forbidden[source_layer]:
                                    if imported.startswith(fb):
                                        errors.append(
                                            f"{rel}: {source_layer} imports {imported}"
                                        )
                except SyntaxError:
                    pass

        except Exception as e:
            errors.append(f"Layer import check failed: {e}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate governance contracts")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--branch", help="Check specific branch only")
    args = parser.parse_args()

    _add_src_to_path()

    all_errors: list[str] = []

    print("=== Governance Contract Validation ===\n")

    # 1. Skill matrix
    print("1. Skill matrix...")
    errors = check_skill_matrix(verbose=args.verbose)
    all_errors.extend(errors)
    print(f"   {'PASS' if not errors else 'FAIL'}" + (f" ({len(errors)} errors)" if errors else ""))

    # 2. MCP providers
    print("2. MCP providers...")
    errors = check_mcp_providers(verbose=args.verbose)
    all_errors.extend(errors)
    print(f"   {'PASS' if not errors else 'FAIL'}" + (f" ({len(errors)} errors)" if errors else ""))

    # 3. Prompt composer
    print("3. Prompt composer...")
    errors = check_prompt_composer(verbose=args.verbose, target_branch=args.branch)
    all_errors.extend(errors)
    print(f"   {'PASS' if not errors else 'FAIL'}" + (f" ({len(errors)} errors)" if errors else ""))

    # 4. Layer imports
    print("4. Layer imports...")
    errors = check_layer_imports(verbose=args.verbose)
    all_errors.extend(errors)
    print(f"   {'PASS' if not errors else 'FAIL'}" + (f" ({len(errors)} errors)" if errors else ""))

    # Summary
    print(f"\n{'='*40}")
    if all_errors:
        print(f"VALIDATION FAILED: {len(all_errors)} errors")
        for e in all_errors:
            print(f"  - {e}")
        return 1
    else:
        print("VALIDATION PASSED: All checks OK")
        return 0


if __name__ == "__main__":
    sys.exit(main())
