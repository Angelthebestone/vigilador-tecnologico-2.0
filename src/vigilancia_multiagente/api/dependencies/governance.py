"""Governance services — system base, prompt composer, contract loader, smart router."""

from __future__ import annotations

from typing import Any

from vigilancia_multiagente.application.evaluation.source_scorer import SourceScorerService
from vigilancia_multiagente.application.governance.contract_loader import GovernanceContractLoader
from vigilancia_multiagente.application.governance.prompt_composer import PromptComposer
from vigilancia_multiagente.application.governance.smart_router import SmartToolRouter
from vigilancia_multiagente.application.governance.system_base_loader import SystemBaseLoader
from vigilancia_multiagente.domain.system_base import SystemBase

from ._singletons import get_source_trust_store


def build_governance_services(s: dict[str, Any]) -> dict[str, Any]:
    """System base, prompt composer, contract loader, smart router."""
    g: dict[str, Any] = {}
    source_trust_repository = get_source_trust_store()
    g["source_trust_repository"] = source_trust_repository
    source_scorer_service = SourceScorerService(repository=source_trust_repository)
    g["source_scorer_service"] = source_scorer_service
    g["smart_router"] = SmartToolRouter(source_scorer=source_scorer_service)
    contracts_root = s["PROJECT_ROOT"] / "specs/002-vigilancia-multiagente/contracts"
    g["contracts_root"] = contracts_root
    g["governance_loader"] = GovernanceContractLoader(
        contracts_root, prompt_loader=s["prompt_loader"]
    )
    g["system_base_loader"] = SystemBaseLoader(contracts_root)

    system_base: SystemBase | None = None
    if s["settings"].system_base_enabled:
        try:
            system_base = g["system_base_loader"].load()
        except Exception as exc:
            import logging

            logging.getLogger(__name__).warning("Failed to load system base: %s", exc)
    g["system_base"] = system_base
    g["prompt_composer"] = PromptComposer(prompt_loader=s["prompt_loader"])
    return g
