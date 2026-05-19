# Tools disponibles por agente

> Generado por `scripts/gen_tools_doc.py` desde la skill matrix
> (`application/governance/contract_loader.py`) y el registro MCP
> (`infra/mcp/provider_registry.py`). Nombres de tool verificados
> contra los repos/documentación oficiales de cada proveedor.
> Si cambias la matrix o el registry, **regenera este documento**.

## Cómo se eligen las tools

`tool_order` **no es una secuencia obligatoria**. `ToolSelector` trata
ese conjunto como las tools *disponibles* y elige una por iteración
según señal (tipo de query, sugerencia del payload previo, afinidad),
**no por posición**. La única secuencia forzada es la cadena
binario→texto (`download_paper` → `read_paper`/`convert_to_markdown`).

Para scraping/extracción el agente es **libre de usar `fetch` (MCP
local) primero** y dejar las APIs como último recurso.

## Clasificación de transporte

| Categoría | Significado |
|-----------|-------------|
| **MCP local** | Proceso local STDIO; sin API key ni red para el protocolo (`fetch`, `playwright`, `sandbox`, `arxiv`, `openalex`, `google_scholar`, `markitdown`). |
| **MCP local + API** | Corre local (npx/uvx) pero llama una API externa con key (`brave`, `firecrawl`, `serper`, `minimax-image`). |
| **API (HTTP)** | Cliente MCP habla HTTP directo a un endpoint remoto con key (`tavily`, `exa`, `jina`). |

---

## AVANCES

Señales de avances tecnológicos y tendencias emergentes.

| Tool | Proveedor | Transporte | Capacidad |
|------|-----------|------------|-----------|
| `tavily_search` | tavily | API (HTTP) | búsqueda web |
| `web_search_exa` | exa | API (HTTP) | búsqueda web |
| `firecrawl_search` | firecrawl | MCP local + API | búsqueda + scraping |
| `read_url` | jina | API (HTTP) | extracción de URL |
| `tavily_map` | tavily | API (HTTP) | mapeo de estructura de sitio |
| `search_works` | openalex | MCP local | obras académicas |
| `analyze_topic_trends` | openalex | MCP local | tendencias de tema |
| `get_citation_network` | openalex | MCP local | red de citación |
| `get_trending_topics` | openalex | MCP local | temas emergentes |
| `summarize_paper` | arxiv | MCP local | resumen de paper |
| `execute_code` | sandbox | MCP local | ejecución de código |
| `list_libraries` | sandbox | MCP local | librerías disponibles |
| `visualize` | sandbox | MCP local | charting |
| `understand_image` | minimax-image | MCP local + API | análisis de imágenes |
| `google_search_patents` | serper | MCP local + API | patentes |

---

## COMERCIAL

Dinámicas comerciales, movimientos de mercado y posicionamiento.

| Tool | Proveedor | Transporte | Capacidad |
|------|-----------|------------|-----------|
| `web_search_advanced_exa` | exa | API (HTTP) | búsqueda web avanzada |
| `brave_news_search` | brave | MCP local + API | noticias |
| `firecrawl_search` | firecrawl | MCP local + API | búsqueda + scraping |
| `fetch` | fetch | **MCP local** | extracción HTML estático |
| `browser_navigate` | playwright | **MCP local** | navegación |
| `browser_snapshot` | playwright | **MCP local** | snapshot accesibilidad |
| `tavily_map` | tavily | API (HTTP) | mapeo de estructura de sitio |
| `tavily_extract` | tavily | API (HTTP) | extracción de contenido |
| `execute_code` | sandbox | MCP local | ejecución de código |
| `list_libraries` | sandbox | MCP local | librerías disponibles |
| `visualize` | sandbox | MCP local | charting |
| `understand_image` | minimax-image | MCP local + API | análisis de imágenes |

---

## RIESGO

Señales de riesgo tecnológico, regulatorio o de mercado.

| Tool | Proveedor | Transporte | Capacidad |
|------|-----------|------------|-----------|
| `brave_web_search` | brave | MCP local + API | búsqueda web |
| `fetch` | fetch | **MCP local** | extracción HTML estático |
| `browser_navigate` | playwright | **MCP local** | navegación |
| `browser_snapshot` | playwright | **MCP local** | snapshot accesibilidad |
| `browser_take_screenshot` | playwright | **MCP local** | screenshot |
| `browser_pdf_save` | playwright | **MCP local** | guardar PDF |
| `firecrawl_scrape` | firecrawl | MCP local + API | scraping robusto |
| `firecrawl_crawl` | firecrawl | MCP local + API | crawling profundo |
| `guess_datetime_url` | jina | API (HTTP) | datación de URL |
| `execute_code` | sandbox | MCP local | ejecución de código |
| `list_libraries` | sandbox | MCP local | librerías disponibles |
| `visualize` | sandbox | MCP local | charting |
| `understand_image` | minimax-image | MCP local + API | análisis de imágenes |

---

## PI_NORMATIVA

Cambios normativos, patentes y obligaciones legales.

| Tool | Proveedor | Transporte | Capacidad |
|------|-----------|------------|-----------|
| `search_google_scholar_key_words` | google_scholar | MCP local | búsqueda académica |
| `search_papers` | arxiv | MCP local | búsqueda de papers |
| `download_paper` | arxiv | MCP local | descarga de paper |
| `read_paper` | arxiv | MCP local | lectura de paper |
| `list_papers` | arxiv | MCP local | inventario de papers |
| `summarize_paper` | arxiv | MCP local | resumen de paper |
| `compare_papers` | arxiv | MCP local | comparación de papers |
| `read_url` | jina | API (HTTP) | extracción de URL |
| `search_works` | openalex | MCP local | obras académicas |
| `find_seminal_papers` | openalex | MCP local | papers seminales |
| `execute_code` | sandbox | MCP local | ejecución de código |
| `list_libraries` | sandbox | MCP local | librerías disponibles |
| `visualize` | sandbox | MCP local | charting |
| `understand_image` | minimax-image | MCP local + API | análisis de imágenes |
| `google_search_patents` | serper | MCP local + API | patentes |
| `google_search_scholar` | serper | MCP local + API | académico |

---

## COMPETITIVO

Panorama competitivo, posicionamiento y ventajas diferenciales.

| Tool | Proveedor | Transporte | Capacidad |
|------|-----------|------------|-----------|
| `web_search_advanced_exa` | exa | API (HTTP) | búsqueda web avanzada |
| `brave_news_search` | brave | MCP local + API | noticias |
| `firecrawl_search` | firecrawl | MCP local + API | búsqueda + scraping |
| `fetch` | fetch | **MCP local** | extracción HTML estático |
| `browser_navigate` | playwright | **MCP local** | navegación |
| `browser_snapshot` | playwright | **MCP local** | snapshot accesibilidad |
| `browser_take_screenshot` | playwright | **MCP local** | screenshot |
| `firecrawl_map` | firecrawl | MCP local + API | descubrir URLs del sitio |
| `read_url` | jina | API (HTTP) | extracción de URL |
| `search_authors_by_expertise` | openalex | MCP local | expertos por área |
| `get_author_info` | google_scholar | MCP local | perfil de autor |
| `execute_code` | sandbox | MCP local | ejecución de código |
| `list_libraries` | sandbox | MCP local | librerías disponibles |
| `visualize` | sandbox | MCP local | charting |
| `understand_image` | minimax-image | MCP local + API | análisis de imágenes |
| `google_search_patents` | serper | MCP local + API | patentes |

---

## OPORTUNIDADES

Oportunidades de innovación, colaboración o nuevos mercados.

| Tool | Proveedor | Transporte | Capacidad |
|------|-----------|------------|-----------|
| `tavily_search` | tavily | API (HTTP) | búsqueda web |
| `web_search_exa` | exa | API (HTTP) | búsqueda web |
| `brave_web_search` | brave | MCP local + API | búsqueda web |
| `firecrawl_search` | firecrawl | MCP local + API | búsqueda + scraping |
| `fetch` | fetch | **MCP local** | extracción HTML estático |
| `tavily_map` | tavily | API (HTTP) | mapeo de estructura de sitio |
| `execute_code` | sandbox | MCP local | ejecución de código |
| `list_libraries` | sandbox | MCP local | librerías disponibles |
| `visualize` | sandbox | MCP local | charting |
| `understand_image` | minimax-image | MCP local + API | análisis de imágenes |
| `google_search_patents` | serper | MCP local + API | patentes |

---

## Resumen de cobertura

Total tools registradas en el MCP registry: **87**.
Ampliación tras auditoría contra documentación oficial:

- **Tavily**: +`tavily_map`, +`tavily_crawl`
- **Firecrawl**: +`firecrawl_search/map/crawl/extract/batch_scrape/check_crawl_status`
- **Brave**: +`brave_summarizer`
- **Jina**: +`parallel_read_url`, +`capture_screenshot_url`
- **ArXiv**: +`list_papers/summarize_paper/compare_papers`
- **Serper**: +`google_search_videos/maps/places/reviews/shopping/lens/autocomplete`
- **OpenAlex**: +`autocomplete_search`
- **Playwright**: fix `browser_screenshot`→`browser_take_screenshot`; +`browser_navigate_back/pdf_save/press_key/wait_for/evaluate/console_messages`

