"""Genera docs/tools-by-agent.md desde la skill matrix + provider registry.

Fuente única de verdad: lee contract_loader y provider_registry, así el doc
nunca se desincroniza. Ejecutar tras tocar la matrix o el registry.
"""

from pathlib import Path

from vigilancia_multiagente.application.governance.contract_loader import (
    GovernanceContractLoader,
)
from vigilancia_multiagente.config.settings import Settings
from vigilancia_multiagente.infra.mcp.provider_registry import MCPProviderRegistry

_DESC = {
    "tavily_search": "búsqueda web",
    "tavily_extract": "extracción de contenido",
    "tavily_map": "mapeo de estructura de sitio",
    "tavily_crawl": "crawling de sitio",
    "web_search_exa": "búsqueda web",
    "web_search_advanced_exa": "búsqueda web avanzada",
    "web_fetch_exa": "fetch de URL",
    "firecrawl_scrape": "scraping robusto",
    "firecrawl_search": "búsqueda + scraping",
    "firecrawl_map": "descubrir URLs del sitio",
    "firecrawl_crawl": "crawling profundo",
    "firecrawl_extract": "extracción estructurada (LLM)",
    "firecrawl_batch_scrape": "scraping en lote",
    "firecrawl_check_crawl_status": "estado de crawl",
    "read_url": "extracción de URL",
    "parallel_read_url": "lectura de URLs en paralelo",
    "capture_screenshot_url": "screenshot de URL",
    "search_web": "búsqueda web",
    "guess_datetime_url": "datación de URL",
    "brave_web_search": "búsqueda web",
    "brave_news_search": "noticias",
    "brave_summarizer": "resumen de resultados",
    "search_papers": "búsqueda de papers",
    "download_paper": "descarga de paper",
    "read_paper": "lectura de paper",
    "list_papers": "inventario de papers",
    "summarize_paper": "resumen de paper",
    "compare_papers": "comparación de papers",
    "search_google_scholar_key_words": "búsqueda académica",
    "search_google_scholar_advanced": "búsqueda académica avanzada",
    "get_author_info": "perfil de autor",
    "search_works": "obras académicas",
    "get_citation_network": "red de citación",
    "get_top_cited_works": "más citados",
    "analyze_topic_trends": "tendencias de tema",
    "get_trending_topics": "temas emergentes",
    "compare_research_areas": "comparar áreas",
    "analyze_geographic_distribution": "distribución geográfica",
    "find_seminal_papers": "papers seminales",
    "search_authors_by_expertise": "expertos por área",
    "autocomplete_search": "autocompletado",
    "google_search": "búsqueda Google",
    "google_search_news": "noticias",
    "google_search_scholar": "académico",
    "google_search_patents": "patentes",
    "google_search_images": "imágenes",
    "google_search_videos": "vídeos",
    "google_search_maps": "mapas",
    "google_search_places": "lugares",
    "google_search_reviews": "reseñas",
    "google_search_shopping": "shopping",
    "google_search_lens": "Google Lens",
    "google_search_autocomplete": "autocompletado",
    "webpage_scrape": "scraping de página",
    "fetch": "extracción HTML estático",
    "convert_to_markdown": "conversión a markdown",
    "browser_navigate": "navegación",
    "browser_navigate_back": "volver atrás",
    "browser_snapshot": "snapshot accesibilidad",
    "browser_take_screenshot": "screenshot",
    "browser_pdf_save": "guardar PDF",
    "browser_click": "click",
    "browser_type": "escribir",
    "browser_select_option": "seleccionar opción",
    "browser_hover": "hover",
    "browser_press_key": "pulsar tecla",
    "browser_wait_for": "esperar elemento",
    "browser_evaluate": "ejecutar JS",
    "browser_console_messages": "mensajes de consola",
    "browser_tabs": "pestañas",
    "browser_network_requests": "lista de requests",
    "browser_network_request": "detalle de request",
    "execute_code": "ejecución de código",
    "list_libraries": "librerías disponibles",
    "visualize": "charting",
    "understand_image": "análisis de imágenes",
}

_OBJETIVOS = {
    "AVANCES": "Señales de avances tecnológicos y tendencias emergentes.",
    "COMERCIAL": "Dinámicas comerciales, movimientos de mercado y posicionamiento.",
    "RIESGO": "Señales de riesgo tecnológico, regulatorio o de mercado.",
    "PI_NORMATIVA": "Cambios normativos, patentes y obligaciones legales.",
    "COMPETITIVO": "Panorama competitivo, posicionamiento y ventajas diferenciales.",
    "OPORTUNIDADES": "Oportunidades de innovación, colaboración o nuevos mercados.",
}

_LOCAL_PURE = {
    "fetch",
    "playwright",
    "sandbox",
    "arxiv",
    "google_scholar",
    "openalex",
    "markitdown",
}
_SANDBOX_TOOLS = {"execute_code", "list_libraries", "visualize"}


def _kind(provider: str, transport: str) -> str:
    if transport == "STDIO":
        return "MCP local" if provider in _LOCAL_PURE else "MCP local + API"
    return "API (HTTP)"


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    matrix = GovernanceContractLoader(root).load_skill_matrix()
    registry = MCPProviderRegistry()
    registry.ensure_standard_providers(Settings())

    tool_provider: dict[str, tuple[str, str]] = {}
    for provider in registry.list():
        for tool in provider.enabled_tools:
            tool_provider.setdefault(tool, (provider.name, provider.transport.value))

    out: list[str] = [
        "# Tools disponibles por agente",
        "",
        "> Generado por `scripts/gen_tools_doc.py` desde la skill matrix",
        "> (`application/governance/contract_loader.py`) y el registro MCP",
        "> (`infra/mcp/provider_registry.py`). Nombres de tool verificados",
        "> contra los repos/documentación oficiales de cada proveedor.",
        "> Si cambias la matrix o el registry, **regenera este documento**.",
        "",
        "## Cómo se eligen las tools",
        "",
        "`tool_order` **no es una secuencia obligatoria**. `ToolSelector` trata",
        "ese conjunto como las tools *disponibles* y elige una por iteración",
        "según señal (tipo de query, sugerencia del payload previo, afinidad),",
        "**no por posición**. La única secuencia forzada es la cadena",
        "binario→texto (`download_paper` → `read_paper`/`convert_to_markdown`).",
        "",
        "Para scraping/extracción el agente es **libre de usar `fetch` (MCP",
        "local) primero** y dejar las APIs como último recurso.",
        "",
        "## Clasificación de transporte",
        "",
        "| Categoría | Significado |",
        "|-----------|-------------|",
        "| **MCP local** | Proceso local STDIO; sin API key ni red para el "
        "protocolo (`fetch`, `playwright`, `sandbox`, `arxiv`, `openalex`, "
        "`google_scholar`, `markitdown`). |",
        "| **MCP local + API** | Corre local (npx/uvx) pero llama una API "
        "externa con key (`brave`, `firecrawl`, `serper`, `minimax-image`). |",
        "| **API (HTTP)** | Cliente MCP habla HTTP directo a un endpoint "
        "remoto con key (`tavily`, `exa`, `jina`). |",
        "",
    ]

    for branch, policy in matrix.items():
        out += ["---", "", f"## {branch.value}", "", _OBJETIVOS.get(branch.value, ""), ""]
        out += [
            "| Tool | Proveedor | Transporte | Capacidad |",
            "|------|-----------|------------|-----------|",
        ]
        for tool in policy.tool_order:
            if tool in _SANDBOX_TOOLS:
                provider, transport = "sandbox", "STDIO"
            else:
                provider, transport = tool_provider.get(tool, ("?", "?"))
            knd = _kind(provider, transport)
            bold = "**" if knd == "MCP local" and provider in ("fetch", "playwright") else ""
            out.append(
                f"| `{tool}` | {provider} | {bold}{knd}{bold} | "
                f"{_DESC.get(tool, '-')} |"
            )
        out.append("")

    total = sum(len(p.enabled_tools) for p in registry.list())
    out += [
        "---",
        "",
        "## Resumen de cobertura",
        "",
        f"Total tools registradas en el MCP registry: **{total}**.",
        "Ampliación tras auditoría contra documentación oficial:",
        "",
        "- **Tavily**: +`tavily_map`, +`tavily_crawl`",
        "- **Firecrawl**: +`firecrawl_search/map/crawl/extract/batch_scrape/"
        "check_crawl_status`",
        "- **Brave**: +`brave_summarizer`",
        "- **Jina**: +`parallel_read_url`, +`capture_screenshot_url`",
        "- **ArXiv**: +`list_papers/summarize_paper/compare_papers`",
        "- **Serper**: +`google_search_videos/maps/places/reviews/shopping/"
        "lens/autocomplete`",
        "- **OpenAlex**: +`autocomplete_search`",
        "- **Playwright**: fix `browser_screenshot`→`browser_take_screenshot`; "
        "+`browser_navigate_back/pdf_save/press_key/wait_for/evaluate/"
        "console_messages`",
        "",
    ]

    (root / "docs" / "tools-by-agent.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"escrito docs/tools-by-agent.md ({len(out)} líneas, {total} tools)")


if __name__ == "__main__":
    main()
