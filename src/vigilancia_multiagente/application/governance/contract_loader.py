import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import yaml

from vigilancia_multiagente.domain.models import BranchType
from vigilancia_multiagente.domain.system_base import BranchOverlay

logger = logging.getLogger(__name__)

_SKILL_MATRIX_YAML = (
    Path(__file__).resolve().parents[4] / "config" / "skills" / "skill_matrix_default.yaml"
)


@dataclass(slots=True)
class AgentSkillPolicy:
    branch_type: BranchType
    allowed_tools: tuple[str, ...]
    tool_order: tuple[str, ...]
    timeout_ms_per_tool: dict[str, int]
    retry_limit_per_tool: dict[str, int]
    substitution_policy: str = "none"


def _skill_matrix_from_yaml(path: Path) -> dict[BranchType, AgentSkillPolicy]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise TypeError("skill matrix YAML must be a mapping")
    matrix: dict[BranchType, AgentSkillPolicy] = {}
    for branch_key, entry in raw.items():
        branch_type = BranchType(str(branch_key).upper())
        if not isinstance(entry, dict):
            raise TypeError(f"skill entry for {branch_key} must be a mapping")
        matrix[branch_type] = AgentSkillPolicy(
            branch_type=branch_type,
            allowed_tools=tuple(cast(list[str], entry.get("allowed_tools", ()))),
            tool_order=tuple(cast(list[str], entry.get("tool_order", ()))),
            timeout_ms_per_tool={
                str(k): int(v)
                for k, v in cast(dict[str, Any], entry.get("timeout_ms_per_tool", {})).items()
            },
            retry_limit_per_tool={
                str(k): int(v)
                for k, v in cast(dict[str, Any], entry.get("retry_limit_per_tool", {})).items()
            },
            substitution_policy=str(entry.get("substitution_policy", "none")),
        )
    return matrix


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
        "do_rules": (
            "priorizar fuentes oficiales o de prensa especializada",
            "declarar incertidumbre",
        ),
        "dont_rules": (
            "inventar métricas financieras",
            "inferir participación de mercado sin datos",
        ),
        "uncertainty_handling": "confidence < 0.6 → next_query concreto (≤20 palabras)",
    },
    BranchType.RIESGO: {
        "objective": "Detectar señales de riesgo tecnológico, regulatorio o de mercado que puedan afectar el dominio.",
        "do_rules": ("etiquetar nivel de riesgo (bajo/medio/alto)", "citar fuente"),
        "dont_rules": (
            "especular sin evidencia",
            "mezclar riesgo operativo con estratégico sin distinción",
        ),
        "uncertainty_handling": "confidence < 0.6 → next_query concreto (≤20 palabras)",
    },
    BranchType.PI_NORMATIVA: {
        "objective": "Identificar cambios normativos, patentes relevantes y obligaciones legales en el dominio.",
        "do_rules": ("identificar jurisdicción aplicable", "citar número de patente/norma"),
        "dont_rules": (
            "interpretar textos legales sin disclaimer",
            "inferir aplicabilidad sin verificar jurisdicción",
        ),
        "uncertainty_handling": "confidence < 0.6 → next_query concreto (≤20 palabras)",
    },
    BranchType.COMPETITIVO: {
        "objective": "Analizar el panorama competitivo, posicionamiento de competidores y ventajas diferenciales.",
        "do_rules": (
            "nombrar competidores específicos",
            "citar fuente de inteligencia competitiva",
        ),
        "dont_rules": (
            "hacer juicios de valor sin respaldo",
            "mezclar rumores con hechos confirmados",
        ),
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
        if _SKILL_MATRIX_YAML.exists():
            try:
                return _skill_matrix_from_yaml(_SKILL_MATRIX_YAML)
            except Exception as exc:
                logger.warning(
                    "Failed to load skill matrix from %s, using embedded fallback: %s",
                    _SKILL_MATRIX_YAML,
                    exc,
                )
        return self._embedded_skill_matrix_fallback()

    def _embedded_skill_matrix_fallback(self) -> dict[BranchType, AgentSkillPolicy]:
        return {
            BranchType.AVANCES: AgentSkillPolicy(
                branch_type=BranchType.AVANCES,
                # Conjunto disponible (ToolSelector elige por señal). Tools
                # bibliométricas OpenAlex añadidas: redes de citación y
                # tendencias emergentes son señal central de vigilancia.
                # execute_code/list_libraries/visualize: análisis numérico
                # y charting sobre datos recolectados.
                # understand_image: analizar figuras técnicas, diagramas de
                # patentes, gráficos de tendencias generados por visualize.
                # google_search_patents: búsqueda de patentes vía Google
                # Patents — única tool de patentes del sistema.
                # tavily_map: mapear la estructura de un sitio fuente antes
                # de extraer (descubrir páginas de releases/changelogs).
                # firecrawl_search: búsqueda web con scraping integrado.
                # summarize_paper: resumen estructurado de papers de avance.
                allowed_tools=(
                    "tavily_search",
                    "web_search_exa",
                    "firecrawl_search",
                    "read_url",
                    "tavily_map",
                    "search_works",
                    "analyze_topic_trends",
                    "get_citation_network",
                    "get_trending_topics",
                    "summarize_paper",
                    "execute_code",
                    "list_libraries",
                    "visualize",
                    "understand_image",
                    "google_search_patents",
                ),
                tool_order=(
                    "tavily_search",
                    "web_search_exa",
                    "firecrawl_search",
                    "read_url",
                    "tavily_map",
                    "search_works",
                    "analyze_topic_trends",
                    "get_citation_network",
                    "get_trending_topics",
                    "summarize_paper",
                    "execute_code",
                    "list_libraries",
                    "visualize",
                    "understand_image",
                    "google_search_patents",
                ),
                timeout_ms_per_tool={
                    "tavily_search": 20000,
                    "web_search_exa": 25000,
                    "firecrawl_search": 30000,
                    "read_url": 30000,
                    "tavily_map": 30000,
                    "search_works": 30000,
                    "analyze_topic_trends": 30000,
                    "get_citation_network": 30000,
                    "get_trending_topics": 30000,
                    "summarize_paper": 30000,
                    "execute_code": 120000,
                    "list_libraries": 10000,
                    "visualize": 30000,
                    "understand_image": 30000,
                    "google_search_patents": 30000,
                },
                retry_limit_per_tool={
                    "tavily_search": 2,
                    "web_search_exa": 2,
                    "firecrawl_search": 2,
                    "read_url": 1,
                    "tavily_map": 1,
                    "search_works": 2,
                    "analyze_topic_trends": 2,
                    "get_citation_network": 2,
                    "get_trending_topics": 2,
                    "summarize_paper": 1,
                    "execute_code": 1,
                    "list_libraries": 1,
                    "visualize": 2,
                    "understand_image": 2,
                    "google_search_patents": 2,
                },
            ),
            BranchType.COMERCIAL: AgentSkillPolicy(
                branch_type=BranchType.COMERCIAL,
                # Scraping/extracción: el agente dispone de fetch (MCP local,
                # HTML estático) y browser_navigate/snapshot (Playwright MCP
                # local, sitios con JS/anti-bot) ADEMÁS de tavily_extract
                # (API). No hay orden obligatorio entre ellas — ToolSelector
                # elige por señal; el agente puede preferir fetch primero.
                # execute_code/list_libraries/visualize: cuantificar mercado,
                # proyecciones financieras y charting de reportes.
                # understand_image: analizar capturas de mercado, gráficos
                # financieros y dashboards de competidores.
                # firecrawl_search: búsqueda+scraping de mercado en un paso.
                # tavily_map: descubrir páginas de pricing/producto de un
                # competidor antes de extraer.
                allowed_tools=(
                    "web_search_advanced_exa",
                    "brave_news_search",
                    "firecrawl_search",
                    "fetch",
                    "browser_navigate",
                    "browser_snapshot",
                    "tavily_map",
                    "tavily_extract",
                    "execute_code",
                    "list_libraries",
                    "visualize",
                    "understand_image",
                ),
                tool_order=(
                    "web_search_advanced_exa",
                    "brave_news_search",
                    "firecrawl_search",
                    "fetch",
                    "browser_navigate",
                    "browser_snapshot",
                    "tavily_map",
                    "tavily_extract",
                    "execute_code",
                    "list_libraries",
                    "visualize",
                    "understand_image",
                ),
                timeout_ms_per_tool={
                    "web_search_advanced_exa": 25000,
                    "brave_news_search": 20000,
                    "firecrawl_search": 30000,
                    "fetch": 25000,
                    "browser_navigate": 60000,
                    "browser_snapshot": 30000,
                    "tavily_map": 30000,
                    "tavily_extract": 25000,
                    "execute_code": 120000,
                    "list_libraries": 10000,
                    "visualize": 30000,
                    "understand_image": 30000,
                },
                retry_limit_per_tool={
                    "web_search_advanced_exa": 2,
                    "brave_news_search": 2,
                    "firecrawl_search": 2,
                    "fetch": 2,
                    "browser_navigate": 2,
                    "browser_snapshot": 1,
                    "tavily_map": 1,
                    "tavily_extract": 1,
                    "execute_code": 1,
                    "list_libraries": 1,
                    "visualize": 2,
                    "understand_image": 2,
                },
            ),
            BranchType.RIESGO: AgentSkillPolicy(
                branch_type=BranchType.RIESGO,
                # Scraping/extracción: fetch (MCP local) y browser_navigate/
                # snapshot (Playwright MCP local) disponibles ADEMÁS de
                # firecrawl_scrape (API). Sin orden obligatorio — el agente
                # puede ir a fetch primero y dejar firecrawl como último
                # recurso si lo considera.
                # execute_code: calcular probabilidades de riesgo, analizar
                # frecuencias de incidentes, modelos de severidad.
                # understand_image: analizar diagramas de vulnerabilidad,
                # capturas de incidentes de seguridad.
                # firecrawl_crawl: recorrer un sitio (avisos de seguridad,
                # CVE feeds) más allá de una página. browser_take_screenshot
                # /browser_pdf_save: capturar evidencia de incidentes.
                allowed_tools=(
                    "brave_web_search",
                    "fetch",
                    "browser_navigate",
                    "browser_snapshot",
                    "browser_take_screenshot",
                    "browser_pdf_save",
                    "firecrawl_scrape",
                    "firecrawl_crawl",
                    "guess_datetime_url",
                    "execute_code",
                    "list_libraries",
                    "visualize",
                    "understand_image",
                ),
                tool_order=(
                    "brave_web_search",
                    "fetch",
                    "browser_navigate",
                    "browser_snapshot",
                    "browser_take_screenshot",
                    "browser_pdf_save",
                    "firecrawl_scrape",
                    "firecrawl_crawl",
                    "guess_datetime_url",
                    "execute_code",
                    "list_libraries",
                    "visualize",
                    "understand_image",
                ),
                timeout_ms_per_tool={
                    "brave_web_search": 20000,
                    "fetch": 25000,
                    "browser_navigate": 60000,
                    "browser_snapshot": 30000,
                    "browser_take_screenshot": 30000,
                    "browser_pdf_save": 30000,
                    "firecrawl_scrape": 35000,
                    "firecrawl_crawl": 90000,
                    "guess_datetime_url": 15000,
                    "execute_code": 120000,
                    "list_libraries": 10000,
                    "visualize": 30000,
                    "understand_image": 30000,
                },
                retry_limit_per_tool={
                    "brave_web_search": 2,
                    "fetch": 2,
                    "browser_navigate": 2,
                    "browser_snapshot": 1,
                    "browser_take_screenshot": 1,
                    "browser_pdf_save": 1,
                    "firecrawl_scrape": 1,
                    "firecrawl_crawl": 1,
                    "guess_datetime_url": 1,
                    "execute_code": 1,
                    "list_libraries": 1,
                    "visualize": 2,
                    "understand_image": 2,
                },
            ),
            BranchType.PI_NORMATIVA: AgentSkillPolicy(
                branch_type=BranchType.PI_NORMATIVA,
                # Conjunto disponible (ToolSelector elige por señal, no por
                # orden). Cadena ArXiv completa: search→download→read; sin
                # read_paper el agente encontraba papers pero no los leía.
                # execute_code: análisis de redes de citación, métricas de
                # patentabilidad, clusters de prior art.
                # understand_image: analizar figuras de patentes, diagramas
                # técnicos en papers, esquemas regulatorios.
                # google_search_patents: búsqueda de patentes vía Google
                # Patents (única tool de patentes del sistema).
                # google_search_scholar: complemento a OpenAlex para
                # cobertura académica vía Google Scholar.
                # summarize_paper/compare_papers: resumir y comparar prior
                # art y papers normativos sin leerlos enteros. list_papers:
                # inventario de papers ya descargados en la sesión.
                allowed_tools=(
                    "search_google_scholar_key_words",
                    "search_papers",
                    "download_paper",
                    "read_paper",
                    "list_papers",
                    "summarize_paper",
                    "compare_papers",
                    "read_url",
                    "search_works",
                    "find_seminal_papers",
                    "execute_code",
                    "list_libraries",
                    "visualize",
                    "understand_image",
                    "google_search_patents",
                    "google_search_scholar",
                ),
                tool_order=(
                    "search_google_scholar_key_words",
                    "search_papers",
                    "download_paper",
                    "read_paper",
                    "list_papers",
                    "summarize_paper",
                    "compare_papers",
                    "read_url",
                    "search_works",
                    "find_seminal_papers",
                    "execute_code",
                    "list_libraries",
                    "visualize",
                    "understand_image",
                    "google_search_patents",
                    "google_search_scholar",
                ),
                timeout_ms_per_tool={
                    "search_google_scholar_key_words": 25000,
                    "search_papers": 25000,
                    "download_paper": 30000,
                    "read_paper": 25000,
                    "list_papers": 10000,
                    "summarize_paper": 30000,
                    "compare_papers": 35000,
                    "read_url": 30000,
                    "search_works": 30000,
                    "find_seminal_papers": 30000,
                    "execute_code": 120000,
                    "list_libraries": 10000,
                    "visualize": 30000,
                    "understand_image": 30000,
                    "google_search_patents": 30000,
                    "google_search_scholar": 30000,
                },
                retry_limit_per_tool={
                    "search_google_scholar_key_words": 2,
                    "search_papers": 2,
                    "download_paper": 2,
                    "read_paper": 1,
                    "list_papers": 1,
                    "summarize_paper": 1,
                    "compare_papers": 1,
                    "read_url": 1,
                    "search_works": 2,
                    "find_seminal_papers": 2,
                    "execute_code": 1,
                    "list_libraries": 1,
                    "visualize": 2,
                    "understand_image": 2,
                    "google_search_patents": 2,
                    "google_search_scholar": 2,
                },
            ),
            BranchType.COMPETITIVO: AgentSkillPolicy(
                branch_type=BranchType.COMPETITIVO,
                # search_authors_by_expertise + get_author_info: mapear
                # líderes técnicos y expertos de competidores era capacidad
                # registrada pero nunca invocada por ningún sistema.
                # execute_code: matrices de posicionamiento competitivo,
                # análisis de市场份额, proyecciones de competitividad.
                # understand_image: analizar capturas de productos
                # competidores, dashboards públicos, infografías.
                # google_search_patents: analizar carteras de patentes de
                # competidores, identificar barreras de entrada por IP.
                # Scraping/extracción: fetch + browser_navigate/snapshot (MCP
                # locales) disponibles junto a read_url (API jina). Sin orden
                # obligatorio — el agente elige la vía por señal.
                # firecrawl_map: descubrir estructura del sitio de un
                # competidor (líneas de producto, careers, prensa).
                # browser_take_screenshot: capturar evidencia visual de
                # productos/landing de competidores.
                allowed_tools=(
                    "web_search_advanced_exa",
                    "brave_news_search",
                    "firecrawl_search",
                    "fetch",
                    "browser_navigate",
                    "browser_snapshot",
                    "browser_take_screenshot",
                    "firecrawl_map",
                    "read_url",
                    "search_authors_by_expertise",
                    "get_author_info",
                    "execute_code",
                    "list_libraries",
                    "visualize",
                    "understand_image",
                    "google_search_patents",
                ),
                tool_order=(
                    "web_search_advanced_exa",
                    "brave_news_search",
                    "firecrawl_search",
                    "fetch",
                    "browser_navigate",
                    "browser_snapshot",
                    "browser_take_screenshot",
                    "firecrawl_map",
                    "read_url",
                    "search_authors_by_expertise",
                    "get_author_info",
                    "execute_code",
                    "list_libraries",
                    "visualize",
                    "understand_image",
                    "google_search_patents",
                ),
                timeout_ms_per_tool={
                    "web_search_advanced_exa": 25000,
                    "brave_news_search": 20000,
                    "firecrawl_search": 30000,
                    "fetch": 25000,
                    "browser_navigate": 60000,
                    "browser_snapshot": 30000,
                    "browser_take_screenshot": 30000,
                    "firecrawl_map": 30000,
                    "read_url": 30000,
                    "search_authors_by_expertise": 30000,
                    "get_author_info": 25000,
                    "execute_code": 120000,
                    "list_libraries": 10000,
                    "visualize": 30000,
                    "understand_image": 30000,
                    "google_search_patents": 30000,
                },
                retry_limit_per_tool={
                    "web_search_advanced_exa": 2,
                    "brave_news_search": 2,
                    "firecrawl_search": 2,
                    "fetch": 2,
                    "browser_navigate": 2,
                    "browser_snapshot": 1,
                    "browser_take_screenshot": 1,
                    "firecrawl_map": 1,
                    "read_url": 1,
                    "search_authors_by_expertise": 2,
                    "get_author_info": 2,
                    "execute_code": 1,
                    "list_libraries": 1,
                    "visualize": 2,
                    "understand_image": 2,
                    "google_search_patents": 2,
                },
            ),
            BranchType.OPORTUNIDADES: AgentSkillPolicy(
                branch_type=BranchType.OPORTUNIDADES,
                # execute_code: análisis numérico y proyecciones sobre
                # datos recolectados (cuantificar oportunidad potencial).
                # visualize: charting para reportes.
                # understand_image: analizar mapas de oportunidad, gráficos
                # de mercado, infografías de tendencias emergentes.
                # google_search_patents: identificar oportunidades de
                # innovación en espacios no patentados.
                # fetch (MCP local): extraer páginas de oportunidad detectadas
                # sin gastar API. Sin orden obligatorio.
                # firecrawl_search: búsqueda+scraping de señales de oportunidad.
                # tavily_map: mapear un sitio/programa de innovación.
                allowed_tools=(
                    "tavily_search",
                    "web_search_exa",
                    "brave_web_search",
                    "firecrawl_search",
                    "fetch",
                    "tavily_map",
                    "execute_code",
                    "list_libraries",
                    "visualize",
                    "understand_image",
                    "google_search_patents",
                ),
                tool_order=(
                    "tavily_search",
                    "web_search_exa",
                    "brave_web_search",
                    "firecrawl_search",
                    "fetch",
                    "tavily_map",
                    "execute_code",
                    "list_libraries",
                    "visualize",
                    "understand_image",
                    "google_search_patents",
                ),
                timeout_ms_per_tool={
                    "tavily_search": 20000,
                    "web_search_exa": 25000,
                    "brave_web_search": 20000,
                    "firecrawl_search": 30000,
                    "fetch": 25000,
                    "tavily_map": 30000,
                    "execute_code": 120000,
                    "list_libraries": 10000,
                    "visualize": 30000,
                    "understand_image": 30000,
                    "google_search_patents": 30000,
                },
                retry_limit_per_tool={
                    "tavily_search": 2,
                    "web_search_exa": 2,
                    "brave_web_search": 2,
                    "firecrawl_search": 2,
                    "fetch": 2,
                    "tavily_map": 1,
                    "execute_code": 1,
                    "list_libraries": 1,
                    "visualize": 2,
                    "understand_image": 2,
                    "google_search_patents": 2,
                },
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
            branch_data = {**branch_data, **overrides}
        except (FileNotFoundError, KeyError, TypeError):
            logger.debug("Using built-in branch overlay for %s", branch_type.value)

        return BranchOverlay(
            branch_type=branch_type,
            objective=str(
                branch_data.get(
                    "objective",
                    f"Generate {branch_type.value.lower()} findings with strong evidence",
                )
            ),
            required_context=("user_query", "temporal_window", "prior_findings"),
            output_schema={
                "findings": "array",
                "sources": "array",
                "confidence": "float",
                "needs_follow_up": "bool",
                "next_query": "string",
            },
            quality_criteria=("evidence_per_finding", "coverage_subtopics", "deduplicated_sources"),
            do_rules=tuple(cast(tuple[str, ...], branch_data.get("do_rules", ("cite_sources", "declare_uncertainty")))),
            dont_rules=tuple(
                cast(tuple[str, ...], branch_data.get("dont_rules", ("invent_data", "claim_causality_without_support")))
            ),
            uncertainty_handling=str(
                branch_data.get(
                    "uncertainty_handling",
                    "Set confidence < 0.6 and provide one concrete next_query",
                )
            ),
            version="1.0.0",
        )


def _parse_prompt_overlay(text: str) -> dict[str, object]:
    """Parse a branch prompt file into overlay fields.

    Supports two formats:

    **HTML format** (current)::

        <task>Objective text</task>
        <rules type="do">
          <rule>rule1</rule>
          <rule>rule2</rule>
        </rules>
        <rules type="dont">
          <rule>rule1</rule>
        </rules>
        <uncertainty>
          <condition>confidence &lt; 0.6</condition>
          <action>next_query concreto</action>
        </uncertainty>

    **Plain-text format** (legacy)::

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

    # Try HTML format first
    html_objective = _html_extract(text, "task")
    if html_objective:
        result["objective"] = html_objective
        result["do_rules"] = tuple(_html_extract_all(text, "rules", attrs={"type": "do"}))
        result["dont_rules"] = tuple(_html_extract_all(text, "rules", attrs={"type": "dont"}))
        uncertainty = _html_extract(text, "uncertainty")
        if uncertainty:
            condition = _html_extract(uncertainty, "condition") or "confidence < 0.6"
            action = _html_extract(uncertainty, "action") or ""
            result["uncertainty_handling"] = f"{condition} → {action}"
        return result

    # Fallback to plain-text format
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("Objective:"):
            current_key = "objective"
            result[current_key] = stripped[len("Objective:") :].strip()
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
            result["uncertainty_handling"] = stripped[len("Uncertainty handling:") :].strip()
        elif current_key in ("do_rules", "dont_rules") and stripped.startswith("- "):
            current_list.append(stripped[2:])
    _flush_list(result, current_key, current_list)
    return result


def _html_extract(text: str, tag: str, attrs: dict[str, str] | None = None) -> str:
    """Extract text content of the first occurrence of ``<tag attrs...>...</tag>``."""
    attr_pattern = ""
    if attrs:
        attr_pattern = "".join(f'\\s+{k}="{re.escape(v)}"' for k, v in attrs.items())
    m = re.search(f"<{tag}{attr_pattern}\\s*>(.*?)</{tag}>", text, re.DOTALL)
    return m.group(1).strip() if m else ""


def _html_extract_all(text: str, tag: str, attrs: dict[str, str] | None = None) -> list[str]:
    """Extract text content of all ``<child_tag>...</child_tag>`` inside a parent ``<tag attrs...>``.

    The child tag is derived by removing trailing ``s`` from the parent tag
    (e.g. ``rules`` → child ``rule``, ``items`` → child ``item``).
    """
    child_tag = tag[:-1] if tag.endswith("s") else tag
    attr_pattern = ""
    if attrs:
        attr_pattern = "".join(f'\\s+{k}="{re.escape(v)}"' for k, v in attrs.items())
    parent_m = re.search(f"<{tag}{attr_pattern}\\s*>(.*?)</{tag}>", text, re.DOTALL)
    if parent_m:
        return re.findall(f"<{child_tag}>(.*?)</{child_tag}>", parent_m.group(1), re.DOTALL)
    return re.findall(f"<{child_tag}>(.*?)</{child_tag}>", text, re.DOTALL)


def _flush_list(result: dict[str, object], key: str | None, items: list[str]) -> None:
    if key and key in ("do_rules", "dont_rules") and items:
        result[key] = tuple(items)
