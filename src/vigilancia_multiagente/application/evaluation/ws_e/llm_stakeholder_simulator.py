"""LlmStakeholderSimulator — spec 007 T025 (WS-E).

Simula la critica de un stakeholder (investor/regulator/competitor/academic)
usando `LLMClient` con un prompt por tipo en `prompts/evaluation/stakeholder_<type>.txt`.

Fallo del LLM -> StepError(severity=warning) y simulacion vacia.
"""

from __future__ import annotations

import logging
from uuid import UUID

from vigilancia_multiagente.domain.evaluation_entities import (
    StakeholderSimulation,
    StakeholderType,
)
from vigilancia_multiagente.domain.models import FinalReport
from vigilancia_multiagente.domain.pipeline_errors import (
    StepError,
    StepErrorSeverity,
    Workstream,
)
from vigilancia_multiagente.domain.ports.llm_client import LLMClient
from vigilancia_multiagente.domain.ports.prompt_loader import PromptLoader
from vigilancia_multiagente.domain.system_base import MiniMaxMessage

logger = logging.getLogger(__name__)


class LlmStakeholderSimulator:
    """Adapter LLM. Errores se acumulan en la lista de errores del contexto."""

    def __init__(
        self,
        llm: LLMClient,
        prompt_loader: PromptLoader,
        errors_sink: list[StepError] | None = None,
    ) -> None:
        self._llm = llm
        self._prompt_loader = prompt_loader
        self._errors = errors_sink

    async def simulate(
        self,
        report: FinalReport,
        stakeholder: str,
    ) -> StakeholderSimulation:
        try:
            stakeholder_type = StakeholderType(stakeholder)
        except ValueError as exc:
            self._record_error(report.session_id, exc)
            return _empty(report.session_id, stakeholder)

        prompt_path = f"evaluation/stakeholder_{stakeholder_type.value}.txt"
        try:
            prompt = self._prompt_loader.load(prompt_path)
        except FileNotFoundError as exc:
            self._record_error(report.session_id, exc, context={"prompt": prompt_path})
            return _empty(report.session_id, stakeholder_type.value)

        messages = [
            MiniMaxMessage(role="system", content=prompt),
            MiniMaxMessage(role="user", content=report.markdown or report.executive_summary),
        ]
        try:
            response = await self._llm.complete(messages)
        except Exception as exc:  # noqa: BLE001 — adapter de frontera externa
            logger.warning("LlmStakeholderSimulator failed: %s", exc, exc_info=True)
            self._record_error(report.session_id, exc, context={"stakeholder": stakeholder})
            return _empty(report.session_id, stakeholder_type.value)

        content = str(getattr(response, "content", "") or "")
        counterpoints = [
            line.lstrip("-•* ").strip()
            for line in content.splitlines()
            if line.lstrip().startswith(("-", "•", "*"))
        ]
        critique = "\n".join(
            line for line in content.splitlines() if not line.lstrip().startswith(("-", "•", "*"))
        ).strip()
        return StakeholderSimulation(
            report_id=report.session_id,
            stakeholder_type=stakeholder_type,
            critique=critique,
            counterpoints=counterpoints,
        )

    def _record_error(
        self,
        report_id: UUID,
        exc: BaseException,
        *,
        context: dict[str, object] | None = None,
    ) -> None:
        if self._errors is None:
            return
        full_context: dict[str, object] = {"report_id": str(report_id)}
        if context:
            full_context.update(context)
        self._errors.append(
            StepError(
                workstream=Workstream.WS_E,
                step_name="LlmStakeholderSimulator.simulate",
                reason=str(exc) or exc.__class__.__name__,
                exception_type=exc.__class__.__name__,
                context=full_context,
                severity=StepErrorSeverity.WARNING,
            )
        )


def _empty(report_id: UUID, stakeholder: str) -> StakeholderSimulation:
    try:
        stype = StakeholderType(stakeholder)
    except ValueError:
        stype = StakeholderType.ACADEMIC
    return StakeholderSimulation(
        report_id=report_id,
        stakeholder_type=stype,
        critique="",
        counterpoints=[],
    )
