from dataclasses import dataclass
import logging
from pathlib import Path

from vigilancia_multiagente.domain.models import BranchType
from vigilancia_multiagente.domain.system_base import BranchOverlay

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AgentSkillPolicy:
    branch_type: BranchType
    allowed_tools: tuple[str, ...]
    tool_order: tuple[str, ...]
    timeout_ms_per_tool: dict[str, int]
    retry_limit_per_tool: dict[str, int]
    substitution_policy: str = "none"


# Branch-specific overlay definitions aligned with agent-governance.md section 2.
_BRANCH_OVERLAYS: dict[BranchType, dict[str, object]] = {
    BranchType.AVANCES: {
        "objective": "Identificar señales de avances tecnológicos y tendencias emergentes en el dominio de la consulta.",
        "do_rules": ("citar fuentes con URL", "declarar incertidumbre"),
        "dont_rules": ("inventar datos", "inferir causalidad sin soporte"),
        "uncertainty_handling": "confidence < 0.6 → next_query concreto (≤20 palabras)",
    },
    BranchType.COMERCIAL: {
        "objective": "Identificar dinámicas comerciales, movimientos de mercado y posicionamiento de actores relevantes.",
        "do_rules": ("priorizar fuentes oficiales o de prensa especializada", "declarar incertidumbre"),
        "dont_rules": ("inventar métricas financieras", "inferir participación de mercado sin datos"),
        "uncertainty_handling": "confidence < 0.6 → next_query concreto (≤20 palabras)",
    },
    BranchType.RIESGO: {
        "objective": "Detectar señales de riesgo tecnológico, regulatorio o de mercado que puedan afectar el dominio.",
        "do_rules": ("etiquetar nivel de riesgo (bajo/medio/alto)", "citar fuente"),
        "dont_rules": ("especular sin evidencia", "mezclar riesgo operativo con estratégico sin distinción"),
        "uncertainty_handling": "confidence < 0.6 → next_query concreto (≤20 palabras)",
    },
    BranchType.PI_NORMATIVA: {
        "objective": "Identificar cambios normativos, patentes relevantes y obligaciones legales en el dominio.",
        "do_rules": ("identificar jurisdicción aplicable", "citar número de patente/norma"),
        "dont_rules": ("interpretar textos legales sin disclaimer", "inferir aplicabilidad sin verificar jurisdicción"),
        "uncertainty_handling": "confidence < 0.6 → next_query concreto (≤20 palabras)",
    },
    BranchType.COMPETITIVO: {
        "objective": "Analizar el panorama competitivo, posicionamiento de competidores y ventajas diferenciales.",
        "do_rules": ("nombrar competidores específicos", "citar fuente de inteligencia competitiva"),
        "dont_rules": ("hacer juicios de valor sin respaldo", "mezclar rumores con hechos confirmados"),
        "uncertainty_handling": "confidence < 0.6 → next_query concreto (≤20 palabras)",
    },
    BranchType.OPORTUNIDADES: {
        "objective": "Identificar oportunidades de innovación, colaboración o nuevos mercados en el dominio.",
        "do_rules": ("cuantificar impacto potencial cuando sea posible", "citar fuente"),
        "dont_rules": ("prometer retornos sin datos", "confundir oportunidad con riesgo"),
        "uncertainty_handling": "confidence < 0.6 → next_query concreto (≤20 palabras)",
    },
}


class GovernanceContractLoader:
    def __init__(self, contracts_root: Path) -> None:
        self._contracts_root = contracts_root

    def load_skill_matrix(self) -> dict[BranchType, AgentSkillPolicy]:
        return {
            BranchType.AVANCES: AgentSkillPolicy(
                branch_type=BranchType.AVANCES,
                allowed_tools=("tavily_search", "web_search_exa", "read_url"),
                tool_order=("tavily_search", "web_search_exa", "read_url"),
                timeout_ms_per_tool={"tavily_search": 20000, "web_search_exa": 25000, "read_url": 30000},
                retry_limit_per_tool={"tavily_search": 2, "web_search_exa": 2, "read_url": 1},
            ),
            BranchType.COMERCIAL: AgentSkillPolicy(
                branch_type=BranchType.COMERCIAL,
                allowed_tools=("web_search_advanced_exa", "brave_news_search", "tavily_extract"),
                tool_order=("web_search_advanced_exa", "brave_news_search", "tavily_extract"),
                timeout_ms_per_tool={"web_search_advanced_exa": 25000, "brave_news_search": 20000, "tavily_extract": 25000},
                retry_limit_per_tool={"web_search_advanced_exa": 2, "brave_news_search": 2, "tavily_extract": 1},
            ),
            BranchType.RIESGO: AgentSkillPolicy(
                branch_type=BranchType.RIESGO,
                allowed_tools=("brave_web_search", "firecrawl_scrape", "guess_datetime_url"),
                tool_order=("brave_web_search", "firecrawl_scrape", "guess_datetime_url"),
                timeout_ms_per_tool={"brave_web_search": 20000, "firecrawl_scrape": 35000, "guess_datetime_url": 15000},
                retry_limit_per_tool={"brave_web_search": 2, "firecrawl_scrape": 1, "guess_datetime_url": 1},
            ),
            BranchType.PI_NORMATIVA: AgentSkillPolicy(
                branch_type=BranchType.PI_NORMATIVA,
                allowed_tools=("search_google_scholar_key_words", "search_papers", "read_url"),
                tool_order=("search_google_scholar_key_words", "search_papers", "read_url"),
                timeout_ms_per_tool={"search_google_scholar_key_words": 25000, "search_papers": 25000, "read_url": 30000},
                retry_limit_per_tool={"search_google_scholar_key_words": 2, "search_papers": 2, "read_url": 1},
            ),
            BranchType.COMPETITIVO: AgentSkillPolicy(
                branch_type=BranchType.COMPETITIVO,
                allowed_tools=("web_search_advanced_exa", "brave_news_search", "read_url"),
                tool_order=("web_search_advanced_exa", "brave_news_search", "read_url"),
                timeout_ms_per_tool={"web_search_advanced_exa": 25000, "brave_news_search": 20000, "read_url": 30000},
                retry_limit_per_tool={"web_search_advanced_exa": 2, "brave_news_search": 2, "read_url": 1},
            ),
            BranchType.OPORTUNIDADES: AgentSkillPolicy(
                branch_type=BranchType.OPORTUNIDADES,
                allowed_tools=("tavily_search", "web_search_exa", "brave_web_search"),
                tool_order=("tavily_search", "web_search_exa", "brave_web_search"),
                timeout_ms_per_tool={"tavily_search": 20000, "web_search_exa": 25000, "brave_web_search": 20000},
                retry_limit_per_tool={"tavily_search": 2, "web_search_exa": 2, "brave_web_search": 2},
            ),
        }

    def load_branch_overlay(self, branch_type: BranchType) -> BranchOverlay:
        """Load the branch-specific overlay for the given branch type.

        Tries ``src/prompts/branches/{branch_type}.txt`` first;
        falls back to the hardcoded ``_BRANCH_OVERLAYS`` dict.
        """
        branch_data = dict(_BRANCH_OVERLAYS[branch_type])

        try:
            from vigilancia_multiagente.infra.prompts.loader import load_prompt

            overrides = _parse_prompt_overlay(load_prompt(f"branches/{branch_type.value.lower()}"))
            branch_data = {**branch_data, **overrides}  # type: ignore[arg-type]
        except (FileNotFoundError, KeyError, TypeError):
            logger.debug("Using built-in branch overlay for %s", branch_type.value)

        return BranchOverlay(
            branch_type=branch_type,
            objective=str(branch_data.get("objective", f"Generate {branch_type.value.lower()} findings with strong evidence")),
            required_context=("user_query", "temporal_window", "prior_findings"),
            output_schema={
                "findings": "array",
                "sources": "array",
                "confidence": "float",
                "needs_follow_up": "bool",
                "next_query": "string",
            },
            quality_criteria=("evidence_per_finding", "coverage_subtopics", "deduplicated_sources"),
            do_rules=tuple(branch_data.get("do_rules", ("cite_sources", "declare_uncertainty"))),
            dont_rules=tuple(branch_data.get("dont_rules", ("invent_data", "claim_causality_without_support"))),
            uncertainty_handling=str(branch_data.get("uncertainty_handling", "Set confidence < 0.6 and provide one concrete next_query")),
            version="1.0.0",
        )


def _parse_prompt_overlay(text: str) -> dict[str, object]:
    """Parse a branch prompt file into overlay fields.

    Expected format::

        Objective: ...
        Do:
        - rule1
        - rule2
        Don't:
        - rule1
        Uncertainty handling: ...
    """
    result: dict[str, object] = {}
    lines = text.strip().splitlines()
    current_key: str | None = None
    current_list: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("Objective:"):
            current_key = "objective"
            result[current_key] = stripped[len("Objective:"):].strip()
        elif stripped == "Do:":
            _flush_list(result, current_key, current_list)
            current_key = "do_rules"
            current_list = []
        elif stripped == "Don't:":
            _flush_list(result, current_key, current_list)
            current_key = "dont_rules"
            current_list = []
        elif stripped.startswith("Uncertainty handling:"):
            _flush_list(result, current_key, current_list)
            result["uncertainty_handling"] = stripped[len("Uncertainty handling:"):].strip()
        elif current_key in ("do_rules", "dont_rules") and stripped.startswith("- "):
            current_list.append(stripped[2:])
    _flush_list(result, current_key, current_list)
    return result


def _flush_list(result: dict[str, object], key: str | None, items: list[str]) -> None:
    if key and key in ("do_rules", "dont_rules") and items:
        result[key] = tuple(items)

