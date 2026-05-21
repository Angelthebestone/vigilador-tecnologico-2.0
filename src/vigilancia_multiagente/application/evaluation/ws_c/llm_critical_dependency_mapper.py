"""LlmCriticalDependencyMapper — spec 007 T096 (WS-C, FR-C03).

Combina KnowledgeGraphService (006) con prompts dirigidos al LLM
para mapear dependencias criticas de una tecnologia.

Fallo del LLM -> StepError(severity=warning) y lista vacia.
"""

from __future__ import annotations

import json
import logging
import re

from vigilancia_multiagente.application.graph.knowledge_graph_service import (
    KnowledgeGraphService,
)
from vigilancia_multiagente.domain.evaluation_entities import (
    CriticalDependency,
    DependencyKind,
    RiskLevel,
)
from vigilancia_multiagente.domain.models import Finding
from vigilancia_multiagente.domain.pipeline_errors import (
    StepError,
    StepErrorSeverity,
    Workstream,
)
from vigilancia_multiagente.domain.ports.critical_dependency import CriticalDependencyMapper
from vigilancia_multiagente.domain.ports.llm_client import LLMClient
from vigilancia_multiagente.domain.system_base import MiniMaxMessage

logger = logging.getLogger(__name__)

_JSON_BLOCK_RE = re.compile(r"\[.*?\]", re.DOTALL)


class LlmCriticalDependencyMapper(CriticalDependencyMapper):
    """Combina KnowledgeGraphService + LLM prompts para mapear dependencias."""

    def __init__(
        self,
        llm: LLMClient,
        graph_service: KnowledgeGraphService,
        errors_sink: list[StepError] | None = None,
    ) -> None:
        self._llm = llm
        self._graph_service = graph_service
        self._errors = errors_sink

    async def map(
        self,
        technology: str,
        findings: list[Finding],
    ) -> list[CriticalDependency]:
        dependencies: list[CriticalDependency] = []

        # Paso 1: extraer dependencias del grafo de conocimiento
        graph_deps = self._extract_from_graph(technology, findings)
        dependencies.extend(graph_deps)

        # Paso 2: enriquecer con LLM (clasificar dependencias no categorizadas)
        llm_prompt = (
            f"Dada la tecnologia '{technology}', identifica sus dependencias "
            f"criticas externas: materiales, librerias, proveedores o regulaciones. "
            f"Responde SOLO con JSON array, cada item con: "
            f"name (str), dependency_kind (material|library|vendor|regulation), "
            f"risk_level (low|medium|high).\n\n"
            f"Hallazgos relevantes:\n"
            + "\n".join(
                f"- {f.statement[:200]}" for f in findings
            )
        )

        messages = [
            MiniMaxMessage(role="system", content=(
                "Eres un analista de dependencias tecnologicas. "
                "Responde SOLO con JSON array valido."
            )),
            MiniMaxMessage(role="user", content=llm_prompt),
        ]
        try:
            response = await self._llm.complete(messages)
        except Exception as exc:
            logger.warning("LlmCriticalDependencyMapper LLM failed: %s", exc, exc_info=True)
            self._record_error(exc, context={"technology": technology})
            return dependencies

        content = str(getattr(response, "content", "") or "")
        llm_items = _extract_items(content)
        known_names = {d.name for d in dependencies}
        for item in llm_items:
            name = str(item.get("name", "")).strip()
            if not name or name in known_names:
                continue
            known_names.add(name)
            try:
                kind = DependencyKind(str(item.get("dependency_kind", "library")))
            except ValueError:
                kind = DependencyKind.LIBRARY
            try:
                risk = RiskLevel(str(item.get("risk_level", "medium")))
            except ValueError:
                risk = RiskLevel.MEDIUM
            dependencies.append(
                CriticalDependency(
                    technology=technology,
                    dependency_kind=kind,
                    name=name,
                    risk_level=risk,
                )
            )

        return dependencies

    def _extract_from_graph(
        self,
        technology: str,
        findings: list[Finding],
    ) -> list[CriticalDependency]:
        """Extrae dependencias candidatas del grafo de conocimiento.
        Por ahora retorna lista vacia — la integracion completa con
        GraphPayload requiere acceso al grafo de la sesion actual,
        que se inyectara via wiring en dependencies.py.
        """
        return []

    def _record_error(
        self, exc: BaseException, *, context: dict[str, object] | None = None
    ) -> None:
        if self._errors is None:
            return
        self._errors.append(
            StepError(
                workstream=Workstream.WS_C,
                step_name="LlmCriticalDependencyMapper.map",
                reason=str(exc) or exc.__class__.__name__,
                exception_type=exc.__class__.__name__,
                context=dict(context) if context else {},
                severity=StepErrorSeverity.WARNING,
            )
        )


def _extract_items(text: str) -> list[dict[str, object]]:
    candidate = text.strip()
    try:
        parsed = json.loads(candidate)
        if isinstance(parsed, list):
            return [item for item in parsed if isinstance(item, dict)]
    except json.JSONDecodeError:
        pass
    match = _JSON_BLOCK_RE.search(text)
    if match:
        try:
            parsed = json.loads(match.group(0))
            if isinstance(parsed, list):
                return [item for item in parsed if isinstance(item, dict)]
        except json.JSONDecodeError:
            pass
    return []
