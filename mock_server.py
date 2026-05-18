"""
Mock server para Vigilador Tecnológico 2.0
==========================================
Simula toda la API sin necesidad de MiniMax, PostgreSQL ni claves externas.
Levanta en http://localhost:8000 — el frontend no necesita ningún cambio.

Uso:
    pip install fastapi uvicorn
    python mock_server.py

El flujo completo dura ~35 segundos de ejecución simulada.
Tema de ejemplo: "IA generativa en manufactura automotriz"
"""

import asyncio
import json
import random
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

# ---------------------------------------------------------------------------
# Datos de ejemplo: sesión temática sobre IA generativa en manufactura
# ---------------------------------------------------------------------------

QUERY_EJEMPLO = "IA generativa en manufactura automotriz"

SESSION_ID = str(uuid.uuid4())

# Preguntas de aclaración que el sistema haría
CLARIFICATION_QUESTIONS = [
    {
        "id": "q1",
        "text": "¿El análisis debe enfocarse en fabricantes OEM, proveedores Tier-1, o ambos?",
    },
    {
        "id": "q2",
        "text": "¿Qué región geográfica tiene mayor prioridad: América del Norte, Europa, Asia-Pacífico, o global?",
    },
    {
        "id": "q3",
        "text": "¿El horizonte temporal de interés es corto plazo (1-2 años), mediano (3-5 años), o largo plazo (+5 años)?",
    },
]

# Plan con las 6 ramas
# Entidades recurrentes de sesiones previas (CrossSessionService.preload_session).
# El backend las inyecta como focus_queries "delta" en cada rama (#5: memoria
# cross-session → plan) para re-investigar lo nuevo en vez de partir de cero.
CROSS_SESSION_RECURRING = ["Toyota", "gemelos digitales"]


def _delta_focus(branch: str) -> list[str]:
    return [
        f"new developments on {term} since prior research ({branch.lower()})"
        for term in CROSS_SESSION_RECURRING
    ]


RESEARCH_PLAN = {
    "id": str(uuid.uuid4()),
    "version": 1,
    "requiresApproval": True,
    "globalConstraints": {
        "maxSourcesPerBranch": 15,
        "minConfidenceThreshold": 0.65,
        "outputLanguage": "es",
    },
    "branches": [
        {
            "branchType": "AVANCES",
            "focusQueries": [
                "IA generativa modelos de lenguaje manufactura automotriz 2024",
                "gemelos digitales IA planta automotriz producción",
                "visión computacional control calidad carrocería defectos",
                *_delta_focus("AVANCES"),
            ],
            "mcpProviders": ["tavily", "exa", "jina", "openalex"],
            "priorityWeight": 1.2,
        },
        {
            "branchType": "COMERCIAL",
            "focusQueries": [
                "mercado IA manufactura automotriz valoración 2024 2025",
                "inversión startups IA automotriz financiación rondas",
                "costos implementación IA línea producción ROI",
                *_delta_focus("COMERCIAL"),
            ],
            "mcpProviders": ["exa", "brave", "tavily"],
            "priorityWeight": 1.0,
        },
        {
            "branchType": "RIESGO",
            "focusQueries": [
                "riesgos ciberseguridad sistemas IA fábricas automotrices",
                "fallos IA producción recall automotriz incidentes",
                "dependencia proveedores IA automotriz concentración mercado",
                *_delta_focus("RIESGO"),
            ],
            "mcpProviders": ["brave", "firecrawl", "jina"],
            "priorityWeight": 1.1,
        },
        {
            "branchType": "PI_NORMATIVA",
            "focusQueries": [
                "patentes IA manufactura automotriz 2023 2024 tendencias",
                "regulación IA industria automotriz Europa Estados Unidos",
                "estándares ISO IA sistemas autónomos manufactura",
                *_delta_focus("PI_NORMATIVA"),
            ],
            "mcpProviders": ["google_scholar", "arxiv", "jina", "openalex"],
            "priorityWeight": 0.9,
        },
        {
            "branchType": "COMPETITIVO",
            "focusQueries": [
                "Toyota BMW Volkswagen estrategia IA manufactura",
                "Tesla Gigafactory IA automatización producción",
                "comparativa implementación IA automotriz competidores",
                *_delta_focus("COMPETITIVO"),
            ],
            "mcpProviders": ["exa", "brave", "jina", "openalex", "google_scholar"],
            "priorityWeight": 1.0,
        },
        {
            "branchType": "OPORTUNIDADES",
            "focusQueries": [
                "oportunidades negocio IA manufactura automotriz nicho",
                "mercados emergentes IA automotriz India México",
                "colaboraciones universidad empresa IA automotriz",
                *_delta_focus("OPORTUNIDADES"),
            ],
            "mcpProviders": ["tavily", "exa", "brave"],
            "priorityWeight": 0.95,
        },
    ],
}

# Planner reactivo: señales que el BranchCoordinator procesa mid-execution.
# Una rama detecta un gap/entidad y se inyecta una directiva a otra rama
# (espejo de ReplanAction: trigger_signal → target_branch → directive).
REPLAN_SIGNALS: list[dict] = [
    {
        "signalType": "gap_detected",
        "sourceBranch": "AVANCES",
        "targetBranch": "PI_NORMATIVA",
        "description": "Patente clave citada sin cobertura normativa",
        "directive": "Investigar estado legal de US-2024-318xxx (prior art)",
    },
    {
        "signalType": "entity_discovered",
        "sourceBranch": "COMPETITIVO",
        "targetBranch": "COMERCIAL",
        "description": "Nuevo actor relevante detectado: Cognex Corp.",
        "directive": "Ampliar análisis de mercado incluyendo Cognex",
    },
]

# Iteraciones de razonamiento por rama (lo que muestra AgentDetailPanel)
BRANCH_ITERATIONS: dict[str, list[dict]] = {
    "AVANCES": [
        {
            "stepNumber": 1,
            "reasoning": "Identificando los avances más recientes en modelos de lenguaje aplicados a líneas de ensamblaje automotriz.",
            "toolCall": {
                "tool": "tavily_search",
                "query": "LLM manufacturing assembly line quality 2024",
                "result": "Encontrados 12 artículos relevantes sobre uso de LLMs en control de calidad.",
            },
            "result": "BMW y Toyota lideran con pilotos de IA generativa para detección de defectos en carrocería.",
            "confidence": 0.82,
        },
        {
            "stepNumber": 2,
            "reasoning": "Profundizando en gemelos digitales y su integración con modelos generativos para simulación de manufactura.",
            "toolCall": {
                "tool": "arxiv_search",
                "query": "digital twins generative AI automotive manufacturing simulation",
                "result": "8 papers de 2023-2024 sobre gemelos digitales con IA generativa.",
            },
            "result": "Siemens y NVIDIA lideran la convergencia entre gemelos digitales y IA generativa (Omniverse Industrial).",
            "confidence": 0.88,
        },
        {
            "stepNumber": 3,
            "reasoning": "Revisando estado del arte en visión computacional para control de calidad en pintura y soldadura.",
            "toolCall": {
                "tool": "google_scholar",
                "query": "computer vision quality control automotive paint welding defect 2024",
                "result": "15 publicaciones con tasas de detección >97% usando modelos transformer.",
            },
            "result": "Los modelos Vision Transformer (ViT) superan a CNN clásicos en detección de microfisuras en soldadura.",
            "confidence": 0.91,
        },
        {
            "stepNumber": 4,
            "reasoning": "Cuantificando la evolución bibliométrica del campo con datos estructurados de OpenAlex (citas, año, instituciones) en vez de inferencia sobre texto.",
            "toolCall": {
                "tool": "analyze_topic_trends",
                "query": "generative AI automotive manufacturing 2018-2024",
                "result": "Crecimiento de publicaciones del 41% anual; pico de citas en 2023.",
            },
            "result": "OpenAlex confirma tendencia exponencial: 1.847 trabajos en 2024 vs 312 en 2019; NVIDIA, Siemens y MIT lideran por volumen de citas.",
            "confidence": 0.89,
        },
    ],
    "COMERCIAL": [
        {
            "stepNumber": 1,
            "reasoning": "Mapeando el tamaño y tasa de crecimiento del mercado global de IA en manufactura automotriz.",
            "toolCall": {
                "tool": "tavily_search",
                "query": "AI automotive manufacturing market size CAGR 2024 2030",
                "result": "Múltiples reportes de analistas con proyecciones de mercado.",
            },
            "result": "Mercado valorado en $4.2B en 2024, con CAGR del 28.3% hacia 2030 (proyección: $18.7B).",
            "confidence": 0.85,
        },
        {
            "stepNumber": 2,
            "reasoning": "Analizando rondas de inversión y M&A en startups de IA para manufactura automotriz.",
            "toolCall": {
                "tool": "exa_search",
                "query": "AI automotive manufacturing startup funding rounds 2023 2024",
                "result": "47 transacciones de M&A e inversión identificadas en 18 meses.",
            },
            "result": "Inversión récord de $2.1B en H1 2024, liderada por Mobileye, Cognex y Scale AI.",
            "confidence": 0.79,
        },
    ],
    "RIESGO": [
        {
            "stepNumber": 1,
            "reasoning": "Identificando vectores de riesgo cibernético en sistemas IA conectados dentro de plantas automotrices.",
            "toolCall": {
                "tool": "tavily_search",
                "query": "cybersecurity AI systems automotive factory OT security 2024",
                "result": "Reportes de incidentes y análisis de vulnerabilidades en entornos OT/IT.",
            },
            "result": "El 67% de fabricantes automotrices reportó intentos de intrusión en sistemas OT conectados a IA en 2023.",
            "confidence": 0.87,
        },
        {
            "stepNumber": 2,
            "reasoning": "Revisando casos de fallos de IA que derivaron en recalls o paros de línea.",
            "toolCall": {
                "tool": "brave_search",
                "query": "AI failure automotive production line halt recall incident 2023 2024",
                "result": "6 incidentes documentados con impacto económico cuantificable.",
            },
            "result": "Identificados 6 incidentes donde fallos de modelos IA provocaron paros de línea >4 horas, con pérdidas promedio de $3.2M.",
            "confidence": 0.83,
        },
    ],
    "PI_NORMATIVA": [
        {
            "stepNumber": 1,
            "reasoning": "Analizando la evolución de patentes en IA aplicada a manufactura automotriz por jurisdicción.",
            "toolCall": {
                "tool": "google_scholar",
                "query": "patents generative AI automotive manufacturing USPTO EPO 2023 2024",
                "result": "Base de datos de patentes con 340 registros relevantes.",
            },
            "result": "Toyota lidera con 89 patentes activas en IA para manufactura; seguida de Bosch (72) y Volkswagen (61).",
            "confidence": 0.90,
        },
        {
            "stepNumber": 2,
            "reasoning": "Revisando el marco regulatorio emergente para IA en entornos industriales automotrices.",
            "toolCall": {
                "tool": "fetch",
                "query": "EU AI Act automotive manufacturing compliance requirements 2024",
                "result": "Documentos oficiales de la Comisión Europea y análisis de impacto.",
            },
            "result": "El EU AI Act clasifica los sistemas IA de control de producción como 'Alto Riesgo', requiriendo auditorías obligatorias desde 2026.",
            "confidence": 0.93,
        },
        {
            "stepNumber": 3,
            "reasoning": "Localizando los papers fundacionales (must-cite) sobre IA en manufactura vía OpenAlex para sustentar el análisis de prior art y patentabilidad.",
            "toolCall": {
                "tool": "find_seminal_papers",
                "query": "AI manufacturing process control foundational",
                "result": "7 papers fundacionales con >500 citas, publicados 5+ años atrás.",
            },
            "result": "Identificados 7 trabajos fundacionales que actúan como prior art clave; 3 patentes recientes de Bosch citan directamente a 2 de ellos.",
            "confidence": 0.91,
        },
        {
            "stepNumber": 4,
            "reasoning": "Descargando el paper fundacional más citado para leer su contenido completo (la cadena search→download→read garantiza texto, no PDF crudo).",
            "toolCall": {
                "tool": "download_paper",
                "query": "arxiv:2103.xxxxx foundational AI manufacturing",
                "result": "Paper descargado localmente; pendiente de extracción a texto.",
            },
            "result": "Paper fundacional descargado. download_paper entrega binario — se encadena read_paper para obtener texto procesable.",
            "confidence": 0.88,
        },
        {
            "stepNumber": 5,
            "reasoning": "Extrayendo el texto del paper descargado (read_paper cierra la cadena: el modelo solo procesa texto, no PDFs).",
            "toolCall": {
                "tool": "read_paper",
                "query": "arxiv:2103.xxxxx full text",
                "result": "Texto markdown del paper extraído (~14k palabras).",
            },
            "result": "Reivindicaciones técnicas del paper analizadas: 2 de las 5 patentes de Bosch solapan con el método descrito en la sección 4 — riesgo de prior art confirmado.",
            "confidence": 0.92,
        },
    ],
    "COMPETITIVO": [
        {
            "stepNumber": 1,
            "reasoning": "Mapeando las estrategias de los principales OEM respecto a adopción de IA generativa en manufactura.",
            "toolCall": {
                "tool": "tavily_search",
                "query": "Toyota BMW Volkswagen Mercedes generative AI manufacturing strategy 2024",
                "result": "Reportes anuales y comunicados de prensa de los 5 principales OEM.",
            },
            "result": "Toyota lidera con su 'Toyota Production System AI' ($800M invertidos); BMW con iFACTORY; Volkswagen con su plataforma CARIAD.",
            "confidence": 0.86,
        },
        {
            "stepNumber": 2,
            "reasoning": "Analizando la ventaja competitiva de Tesla por su enfoque nativo de IA en manufactura (Gigafactory).",
            "toolCall": {
                "tool": "exa_search",
                "query": "Tesla Gigafactory AI automation Dojo manufacturing advantage 2024",
                "result": "Análisis técnicos y comparativas de eficiencia productiva.",
            },
            "result": "Tesla produce 1 vehículo cada 40 segundos con 65% menos personal de QC gracias a visión IA; 35% más eficiente que promedio industria.",
            "confidence": 0.88,
        },
        {
            "stepNumber": 3,
            "reasoning": "Mapeando los líderes técnicos de IA en manufactura de los competidores vía OpenAlex (señal: query de tipo 'people' activa search_authors_by_expertise).",
            "toolCall": {
                "tool": "search_authors_by_expertise",
                "query": "AI manufacturing automotive process optimization experts",
                "result": "Top 15 investigadores por h-index, con afiliación institucional/corporativa.",
            },
            "result": "3 de los 5 investigadores líderes en IA-manufactura están afiliados a Toyota Research y Bosch; señal de concentración de talento en 2 competidores.",
            "confidence": 0.84,
        },
    ],
    "OPORTUNIDADES": [
        {
            "stepNumber": 1,
            "reasoning": "Identificando nichos de mercado desatendidos donde IA generativa podría disruptir la cadena de valor automotriz.",
            "toolCall": {
                "tool": "tavily_search",
                "query": "AI automotive manufacturing opportunity niche underserved market 2024",
                "result": "Análisis de gaps tecnológicos en proveedores Tier-2 y Tier-3.",
            },
            "result": "El 78% de proveedores Tier-2/3 aún no han adoptado IA en QC; oportunidad de mercado estimada en $6.8B para 2027.",
            "confidence": 0.81,
        },
        {
            "stepNumber": 2,
            "reasoning": "Explorando oportunidades de colaboración entre universidades tecnológicas y OEMs en LatAm.",
            "toolCall": {
                "tool": "brave_search",
                "query": "Mexico India emerging market AI automotive manufacturing opportunity",
                "result": "Estudios de factibilidad y programas gubernamentales de adopción.",
            },
            "result": "México y la India emergen como hubs de manufactura inteligente: $1.2B en incentivos gubernamentales combinados para adopción de IA en plantas automotrices.",
            "confidence": 0.77,
        },
    ],
}

# Fuentes simuladas
SOURCES = [
    {
        "id": str(uuid.uuid4()),
        "url": "https://arxiv.org/abs/2401.12345",
        "title": "Generative AI for Automotive Quality Control: A Systematic Review",
        "provider": "arxiv",
        "branchType": "AVANCES",
        "accessedAt": "2026-05-16T10:00:00Z",
    },
    {
        "id": str(uuid.uuid4()),
        "url": "https://scholar.google.com/paper/ViT-automotive",
        "title": "Vision Transformers Outperform CNNs in Weld Defect Detection",
        "provider": "google_scholar",
        "branchType": "AVANCES",
        "accessedAt": "2026-05-16T10:01:00Z",
    },
    {
        "id": str(uuid.uuid4()),
        "url": "https://www.marketsandmarkets.com/ai-automotive-2024",
        "title": "AI in Automotive Manufacturing Market Report 2024-2030",
        "provider": "tavily",
        "branchType": "COMERCIAL",
        "accessedAt": "2026-05-16T10:02:00Z",
    },
    {
        "id": str(uuid.uuid4()),
        "url": "https://techcrunch.com/2024/ai-automotive-funding",
        "title": "AI Automotive Startups Raise Record $2.1B in H1 2024",
        "provider": "exa",
        "branchType": "COMERCIAL",
        "accessedAt": "2026-05-16T10:03:00Z",
    },
    {
        "id": str(uuid.uuid4()),
        "url": "https://www.dragos.com/ot-security-automotive-2024",
        "title": "OT Cybersecurity in Connected Automotive Plants",
        "provider": "tavily",
        "branchType": "RIESGO",
        "accessedAt": "2026-05-16T10:04:00Z",
    },
    {
        "id": str(uuid.uuid4()),
        "url": "https://www.iso.org/standard/ai-manufacturing-2024",
        "title": "ISO/IEC 42001 AI Management Systems for Manufacturing",
        "provider": "fetch",
        "branchType": "PI_NORMATIVA",
        "accessedAt": "2026-05-16T10:05:00Z",
    },
    {
        "id": str(uuid.uuid4()),
        "url": "https://eur-lex.europa.eu/ai-act-automotive",
        "title": "EU AI Act Impact Assessment: Automotive Manufacturing",
        "provider": "fetch",
        "branchType": "PI_NORMATIVA",
        "accessedAt": "2026-05-16T10:06:00Z",
    },
    {
        "id": str(uuid.uuid4()),
        "url": "https://www.toyota-global.com/tps-ai-strategy",
        "title": "Toyota Production System AI: $800M Investment Plan",
        "provider": "tavily",
        "branchType": "COMPETITIVO",
        "accessedAt": "2026-05-16T10:07:00Z",
    },
    {
        "id": str(uuid.uuid4()),
        "url": "https://electrek.co/2024/tesla-gigafactory-ai",
        "title": "Tesla Gigafactory: AI-Driven 40-Second Vehicle Cycle",
        "provider": "exa",
        "branchType": "COMPETITIVO",
        "accessedAt": "2026-05-16T10:08:00Z",
    },
    {
        "id": str(uuid.uuid4()),
        "url": "https://www.ifc.org/ai-automotive-latam-2024",
        "title": "AI Adoption in LatAm Automotive: Mexico and India Emerge",
        "provider": "brave",
        "branchType": "OPORTUNIDADES",
        "accessedAt": "2026-05-16T10:09:00Z",
    },
    {
        "id": str(uuid.uuid4()),
        "url": "https://www.mckinsey.com/ai-tier2-automotive",
        "title": "The $6.8B Opportunity: AI for Tier-2/3 Automotive Suppliers",
        "provider": "tavily",
        "branchType": "OPORTUNIDADES",
        "accessedAt": "2026-05-16T10:10:00Z",
    },
    {
        "id": str(uuid.uuid4()),
        "url": "https://patents.google.com/toyota-ai-manufacturing",
        "title": "Toyota AI Manufacturing Patent Portfolio Analysis 2024",
        "provider": "google_scholar",
        "branchType": "PI_NORMATIVA",
        "accessedAt": "2026-05-16T10:11:00Z",
    },
]

# Reporte final
FINAL_REPORT = {
    "sessionId": SESSION_ID,
    "executiveSummary": (
        "La IA generativa está transformando fundamentalmente la manufactura automotriz a escala global. "
        "Con un mercado valorado en **$4.2B en 2024** y una tasa de crecimiento anual del 28.3%, el sector "
        "alcanzará los $18.7B en 2030. Los líderes del mercado —Toyota, Tesla y BMW— han comprometido "
        "inversiones superiores a los $1.5B combinados en los próximos 3 años. Sin embargo, el 78% de "
        "proveedores Tier-2 y Tier-3 permanecen sin adoptar estas tecnologías, creando una ventana de "
        "oportunidad estimada en $6.8B para integradores tecnológicos especializados."
    ),
    "technicalSection": (
        "## Avances Técnicos\n\n"
        "### Modelos de Lenguaje en Líneas de Ensamblaje\n"
        "Los LLMs se están desplegando para optimización de secuencias de ensamblaje, detección de anomalías "
        "en tiempo real y generación automática de instrucciones de trabajo. BMW y Toyota lideran con pilotos "
        "en producción que reportan reducciones del 23% en tiempo de ciclo y 31% menos defectos escapados.\n\n"
        "### Visión Computacional de Nueva Generación\n"
        "Los modelos Vision Transformer (ViT) han superado a las CNN clásicas en detección de microfisuras en "
        "soldadura, con tasas de detección superiores al 97.3%. NVIDIA Omniverse Industrial y Siemens lideran "
        "la integración con gemelos digitales para simulación predictiva de fallos.\n\n"
        "### Gemelos Digitales + IA Generativa\n"
        "La convergencia entre gemelos digitales y modelos generativos permite simular millones de escenarios "
        "de producción antes de implementar cambios en línea. Stellantis reporta ahorros de $180M anuales "
        "mediante esta tecnología en sus plantas de Norteamérica."
    ),
    "commercialSection": (
        "## Análisis Comercial\n\n"
        "### Dinámica de Mercado\n"
        "El mercado global de IA en manufactura automotriz alcanzó $4.2B en 2024 (CAGR: 28.3%). "
        "Norteamérica concentra el 38% del mercado, seguida de Europa (31%) y Asia-Pacífico (27%).\n\n"
        "### Flujos de Inversión\n"
        "H1 2024 registró un récord de $2.1B en inversión en startups especializadas. Las áreas con mayor "
        "actividad son: inspección visual automatizada (34%), optimización de cadena de suministro con IA (28%), "
        "y mantenimiento predictivo avanzado (22%).\n\n"
        "### Retorno de Inversión\n"
        "Las implementaciones maduras reportan ROI promedio de 340% en 3 años, con payback period de 14 meses "
        "para sistemas de inspección visual y 22 meses para plataformas de optimización integral."
    ),
    "riskSection": (
        "## Análisis de Riesgos\n\n"
        "### Riesgos de Ciberseguridad (Crítico)\n"
        "El 67% de fabricantes automotrices reportó intentos de intrusión en sistemas OT conectados a IA en 2023. "
        "La convergencia IT/OT amplía significativamente la superficie de ataque. Incidente notable: hack a "
        "planta de Tier-1 europeo en Q3 2023 causó paro de 3 días y $47M en pérdidas.\n\n"
        "### Riesgo de Fallos en Producción (Alto)\n"
        "Identificados 6 incidentes documentados donde modelos IA produjeron inferencias incorrectas bajo "
        "condiciones de iluminación no estándar, causando paros de línea con pérdidas promedio de $3.2M "
        "por incidente.\n\n"
        "### Dependencia de Proveedores (Moderado)\n"
        "Alta concentración en NVIDIA (chips), Microsoft Azure (infraestructura cloud) y un conjunto reducido "
        "de integradores especializados crea riesgos de dependencia estratégica para los OEM."
    ),
    "crossAnalysis": (
        "## Análisis Cruzado e Integración\n\n"
        "La convergencia de los hallazgos de las seis ramas revela tres patrones estructurales:\n\n"
        "**1. Brecha de Adopción como Oportunidad Estratégica**\n"
        "Mientras los OEM de primer nivel aceleran la adopción (CAGR propio ~35%), el ecosistema Tier-2/3 "
        "permanece en estadios tempranos. Esta asimetría crea una ventana de 24-36 meses para que "
        "integradores y startups especializadas capturen posiciones de mercado defensibles.\n\n"
        "**2. Tensión Regulatoria-Competitiva**\n"
        "El EU AI Act (implementación 2026) impone costos de compliance que los actores europeos deben "
        "absorber, mientras los competidores de Asia-Pacífico operan con menor carga regulatoria. "
        "Esto podría reconfigurar la competitividad relativa en los próximos 3-5 años.\n\n"
        "**3. Consolidación Patentaria como Barrera de Entrada**\n"
        "Toyota, Bosch y Volkswagen acumulan el 63% de las patentes activas en el dominio. "
        "Los entrantes deben optar por estrategias de innovación en espacios no patentados o "
        "licenciamiento activo."
    ),
    "recommendations": [
        {
            "text": "Desarrollar una plataforma de inspección visual IA específica para proveedores Tier-2/3 con modelo de negocio SaaS y tiempo de implementación <30 días. El mercado no atendido representa $6.8B para 2027.",
            "priority": "alta",
            "basedOn": ["COMERCIAL", "OPORTUNIDADES"],
        },
        {
            "text": "Incorporar marcos de seguridad OT (IEC 62443) como diferenciador competitivo en cualquier solución de IA industrial, dado que el 67% de plantas automotrices han sido atacadas. Esto reduce el riesgo percibido del cliente y acelera decisiones de compra.",
            "priority": "alta",
            "basedOn": ["RIESGO", "COMPETITIVO"],
        },
        {
            "text": "Priorizar cumplimiento anticipado del EU AI Act para posicionarse como proveedor preferido en el mercado europeo antes de la implementación obligatoria en 2026. Los OEM europeos buscarán activamente proveedores pre-certificados.",
            "priority": "media",
            "basedOn": ["PI_NORMATIVA", "COMERCIAL"],
        },
        {
            "text": "Explorar colaboraciones con universidades tecnológicas en México e India para desarrollar talento local y acceder a incentivos gubernamentales ($1.2B combinados) en mercados de manufactura automotriz emergentes.",
            "priority": "media",
            "basedOn": ["OPORTUNIDADES", "COMPETITIVO"],
        },
        {
            "text": "Implementar estrategia de propiedad intelectual defensiva, focalizando patentes en nichos no cubiertos por Toyota/Bosch/Volkswagen, especialmente en integración IA con procesos de pintura y acabados.",
            "priority": "baja",
            "basedOn": ["PI_NORMATIVA", "AVANCES"],
        },
    ],
    "totalSourcesConsulted": len(SOURCES),
    "totalLearnings": 28,
    "confidenceScore": 0.847,
    "generatedAt": datetime.now(UTC).isoformat(),
    "markdown": "",  # se rellena abajo
}

# Secciones de inteligencia derivada (las genera el backend de forma
# determinística: FindingImpactScorer, ContradictionAnalyzer,
# WeakSignalDetector, CausalTimelineBuilder). Los títulos deben coincidir
# literalmente con KNOWN_SECTIONS en IntelligenceSections.tsx.
INTELLIGENCE_SECTIONS = "\n\n".join(
    [
        "## Madurez tecnológica\n\n"
        "- **TRL 7-9 · comercialización**\n"
        "- 14 empresas + 9 patentes dominan sobre 6 papers: tecnología en "
        "comercialización.",
        "## Hallazgos priorizados por impacto\n"
        "- `0.871` **vision-defect-detection** — Detección de defectos por visión "
        "alcanza 99.2% de precisión en líneas de Toyota (autoridad 0.95, novedad 0.92, "
        "convergencia 0.85)\n"
        "- `0.764` **predictive-maintenance** — Mantenimiento predictivo reduce paradas "
        "no planificadas 38% en plantas Bosch (autoridad 0.8, novedad 0.9, convergencia 0.85)\n"
        "- `0.612` **digital-twin-roi** — Gemelos digitales con ROI de 340% en 3 años "
        "(autoridad 0.75, novedad 0.82, convergencia 0.7)",
        "## Puntos en disputa\n\n"
        "### digital-twin-roi\n"
        "- **A** (conf. 0.85): Los gemelos digitales reducen el time-to-market 31% según "
        "Stellantis\n"
        "- **B** (conf. 0.60): Los gemelos digitales no muestran ROI medible en plantas "
        "de menos de 500 empleados\n"
        "- _Las fuentes difieren en polaridad sobre un tema compartido; revisar evidencia "
        "antes de concluir._",
        "## Señales débiles emergentes\n\n"
        "- **neuromorphic-inspection** — Emergente: 2 menciones en 2 rama(s), ausente en "
        "investigación previa.\n"
        "- **federated-quality-models** — Emergente: 3 menciones en 2 rama(s), ausente en "
        "investigación previa.\n"
        "- **edge-llm-orchestration** — Emergente: 2 menciones en 2 rama(s), ausente en "
        "investigación previa.",
        "## Trayectoria causal\n\n"
        "- **2021** (research) → **2023** (prototype): research → prototype\n"
        "- **2023** (prototype) → **2024** (funding): prototype → funding\n"
        "- **2024** (funding) → **2026** (market): funding → market",
        "## Verificación adversarial\n\n"
        "El control automático detectó 2 debilidad(es) que el lector debe "
        "considerar:\n\n"
        "- **[unsourced_finding]** Finding sin fuente: «La adopción de IA en "
        "Tier-2 supera el 40% en 2025»\n"
        "- **[unsupported_recommendation]** Recomendación sin respaldo en "
        "hallazgos: «Priorizar alianzas con fabricantes de chips neuromórficos»",
    ]
)

# Construir campo markdown a partir de las secciones
FINAL_REPORT["markdown"] = "\n\n".join(
    [
        f"# Informe: {QUERY_EJEMPLO}",
        f"## Resumen Ejecutivo\n{FINAL_REPORT['executiveSummary']}",
        FINAL_REPORT["technicalSection"],
        FINAL_REPORT["commercialSection"],
        FINAL_REPORT["riskSection"],
        FINAL_REPORT["crossAnalysis"],
        "## Recomendaciones\n"
        + "\n".join(
            f"- **[{r['priority'].upper()}]** {r['text']}" for r in FINAL_REPORT["recommendations"]
        ),
        INTELLIGENCE_SECTIONS,
    ]
)

# Grafo de conocimiento multicapa
# nodeType: TECHNOLOGY | FINDING | SOURCE | CONCEPT | PATENT | PERSON | COMPANY
# En el backend real, los nodos PERSON/COMPANY los produce EntityExtractor
# (spaCy NER: PERSON -> PERSON, ORG -> COMPANY). Aquí están pre-extraídos.
GRAPH_NODES = [
    # --- TECHNOLOGY (estrella) ---
    {
        "id": "n1",
        "nodeType": "TECHNOLOGY",
        "label": "IA Generativa en Manufactura",
        "centrality": 0.95,
        "branchType": "AVANCES",
        "sourceIds": [],
        "confidence": 0.92,
    },
    # --- FINDING (círculo) ---
    {
        "id": "n2",
        "nodeType": "FINDING",
        "label": "Gemelos Digitales",
        "centrality": 0.82,
        "branchType": "AVANCES",
        "sourceIds": [],
        "confidence": 0.88,
    },
    {
        "id": "n3",
        "nodeType": "FINDING",
        "label": "Visión Computacional / ViT",
        "centrality": 0.78,
        "branchType": "AVANCES",
        "sourceIds": [],
        "confidence": 0.91,
    },
    {
        "id": "n4",
        "nodeType": "FINDING",
        "label": "Control de Calidad Automatizado",
        "centrality": 0.75,
        "branchType": "AVANCES",
        "sourceIds": [],
        "confidence": 0.89,
    },
    {
        "id": "n5",
        "nodeType": "FINDING",
        "label": "Mercado $4.2B (CAGR 28.3%)",
        "centrality": 0.88,
        "branchType": "COMERCIAL",
        "sourceIds": [],
        "confidence": 0.85,
    },
    {
        "id": "n6",
        "nodeType": "FINDING",
        "label": "Inversión $2.1B H1 2024",
        "centrality": 0.72,
        "branchType": "COMERCIAL",
        "sourceIds": [],
        "confidence": 0.79,
    },
    {
        "id": "n7",
        "nodeType": "FINDING",
        "label": "ROI 340% en 3 años",
        "centrality": 0.68,
        "branchType": "COMERCIAL",
        "sourceIds": [],
        "confidence": 0.81,
    },
    {
        "id": "n8",
        "nodeType": "FINDING",
        "label": "Ciberseguridad OT/IT",
        "centrality": 0.84,
        "branchType": "RIESGO",
        "sourceIds": [],
        "confidence": 0.87,
    },
    {
        "id": "n9",
        "nodeType": "FINDING",
        "label": "Fallos IA en Producción",
        "centrality": 0.71,
        "branchType": "RIESGO",
        "sourceIds": [],
        "confidence": 0.83,
    },
    {
        "id": "n10",
        "nodeType": "FINDING",
        "label": "Dependencia NVIDIA / Azure",
        "centrality": 0.65,
        "branchType": "RIESGO",
        "sourceIds": [],
        "confidence": 0.76,
    },
    {
        "id": "n12",
        "nodeType": "FINDING",
        "label": "EU AI Act (2026)",
        "centrality": 0.86,
        "branchType": "PI_NORMATIVA",
        "sourceIds": [],
        "confidence": 0.93,
    },
    {
        "id": "n16",
        "nodeType": "FINDING",
        "label": "Brecha Tier-2/3 ($6.8B)",
        "centrality": 0.90,
        "branchType": "OPORTUNIDADES",
        "sourceIds": [],
        "confidence": 0.81,
    },
    {
        "id": "n17",
        "nodeType": "FINDING",
        "label": "Mercados México e India",
        "centrality": 0.70,
        "branchType": "OPORTUNIDADES",
        "sourceIds": [],
        "confidence": 0.77,
    },
    {
        "id": "n18",
        "nodeType": "FINDING",
        "label": "Colaboración Universidad-OEM",
        "centrality": 0.62,
        "branchType": "OPORTUNIDADES",
        "sourceIds": [],
        "confidence": 0.73,
    },
    # --- CONCEPT (rombo) ---
    {
        "id": "c1",
        "nodeType": "CONCEPT",
        "label": "Automatización Industrial",
        "centrality": 0.74,
        "branchType": "AVANCES",
        "sourceIds": [],
        "confidence": 0.85,
    },
    {
        "id": "c2",
        "nodeType": "CONCEPT",
        "label": "Cadena de Suministro",
        "centrality": 0.66,
        "branchType": "COMERCIAL",
        "sourceIds": [],
        "confidence": 0.78,
    },
    {
        "id": "c3",
        "nodeType": "CONCEPT",
        "label": "Regulación IA",
        "centrality": 0.72,
        "branchType": "PI_NORMATIVA",
        "sourceIds": [],
        "confidence": 0.88,
    },
    # --- PATENT (hexágono) ---
    {
        "id": "p1",
        "nodeType": "PATENT",
        "label": "US20230412811 — AI Assembly QC",
        "centrality": 0.80,
        "branchType": "PI_NORMATIVA",
        "sourceIds": [],
        "confidence": 0.90,
    },
    {
        "id": "p2",
        "nodeType": "PATENT",
        "label": "EP4123456 — Digital Twin Mfg",
        "centrality": 0.71,
        "branchType": "PI_NORMATIVA",
        "sourceIds": [],
        "confidence": 0.86,
    },
    {
        "id": "p3",
        "nodeType": "PATENT",
        "label": "JP2024081234 — ViT Weld Detect",
        "centrality": 0.65,
        "branchType": "PI_NORMATIVA",
        "sourceIds": [],
        "confidence": 0.83,
    },
    # --- SOURCE (cuadrado) ---
    {
        "id": "s1",
        "nodeType": "SOURCE",
        "label": "arxiv.org/abs/2401.12345",
        "centrality": 0.55,
        "branchType": "AVANCES",
        "sourceIds": [],
        "confidence": 0.80,
    },
    {
        "id": "s2",
        "nodeType": "SOURCE",
        "label": "marketsandmarkets.com/ai-auto",
        "centrality": 0.50,
        "branchType": "COMERCIAL",
        "sourceIds": [],
        "confidence": 0.75,
    },
    {
        "id": "s3",
        "nodeType": "SOURCE",
        "label": "eur-lex.europa.eu/ai-act",
        "centrality": 0.58,
        "branchType": "PI_NORMATIVA",
        "sourceIds": [],
        "confidence": 0.92,
    },
    # --- PERSON (círculo punteado) ---
    # affiliation proviene de la metadata estructurada de Exa (category="people");
    # es lo que habilita las aristas COMPANY-employs->PERSON.
    {
        "id": "per1",
        "nodeType": "PERSON",
        "label": "Raj Reddy",
        "centrality": 0.60,
        "branchType": "AVANCES",
        "sourceIds": [],
        "confidence": 0.72,
        "affiliation": None,
    },
    {
        "id": "per2",
        "nodeType": "PERSON",
        "label": "Akira Yoshino",
        "centrality": 0.58,
        "branchType": "PI_NORMATIVA",
        "sourceIds": [],
        "confidence": 0.70,
        "affiliation": "Toyota",
    },
    {
        "id": "per3",
        "nodeType": "PERSON",
        "label": "Elon Musk",
        "centrality": 0.75,
        "branchType": "COMPETITIVO",
        "sourceIds": [],
        "confidence": 0.95,
        "affiliation": "Tesla",
    },
    # --- COMPANY (rectángulo) ---
    {
        "id": "co1",
        "nodeType": "COMPANY",
        "label": "Toyota",
        "centrality": 0.85,
        "branchType": "COMPETITIVO",
        "sourceIds": [],
        "confidence": 0.90,
    },
    {
        "id": "co2",
        "nodeType": "COMPANY",
        "label": "Tesla",
        "centrality": 0.83,
        "branchType": "COMPETITIVO",
        "sourceIds": [],
        "confidence": 0.92,
    },
    {
        "id": "co3",
        "nodeType": "COMPANY",
        "label": "NVIDIA",
        "centrality": 0.79,
        "branchType": "COMPETITIVO",
        "sourceIds": [],
        "confidence": 0.88,
    },
    {
        "id": "co4",
        "nodeType": "COMPANY",
        "label": "Bosch",
        "centrality": 0.73,
        "branchType": "COMPETITIVO",
        "sourceIds": [],
        "confidence": 0.85,
    },
    {
        "id": "co5",
        "nodeType": "COMPANY",
        "label": "BMW",
        "centrality": 0.74,
        "branchType": "COMPETITIVO",
        "sourceIds": [],
        "confidence": 0.84,
    },
]

# Vincular sourceIds de los nodos a las fuentes reales (por índice determinista),
# para que "ver fuentes de un nodo" en el frontend devuelva datos coherentes.
_NODE_SOURCE_MAP: dict[str, list[int]] = {
    "n1": [0, 1],
    "n2": [0],
    "n3": [1],
    "n4": [1],
    "n5": [2],
    "n6": [3],
    "n7": [2],
    "n8": [4],
    "n9": [4],
    "n10": [4],
    "n12": [5, 6],
    "n16": [10],
    "n17": [9],
    "n18": [9],
    "p1": [10],
    "p2": [10],
    "p3": [1],
    "s1": [0],
    "s2": [2],
    "s3": [6],
    "co1": [7],
    "co2": [8],
    "co3": [8],
    "co4": [4],
    "co5": [7],
    "per1": [1],
    "per2": [10],
    "per3": [8],
}
for _node in GRAPH_NODES:
    _idxs = _NODE_SOURCE_MAP.get(_node["id"], [])
    _node["sourceIds"] = [SOURCES[i]["id"] for i in _idxs if i < len(SOURCES)]

GRAPH_EDGES = [
    # TECHNOLOGY → hallazgos principales
    {
        "id": "e1",
        "source": "n1",
        "target": "n2",
        "relationType": "habilita",
        "similarityScore": 0.88,
    },
    {
        "id": "e2",
        "source": "n1",
        "target": "n3",
        "relationType": "incluye",
        "similarityScore": 0.85,
    },
    {
        "id": "e3",
        "source": "n1",
        "target": "n5",
        "relationType": "impulsa",
        "similarityScore": 0.87,
    },
    {
        "id": "e4",
        "source": "n1",
        "target": "n8",
        "relationType": "expone_a",
        "similarityScore": 0.81,
    },
    {
        "id": "e5",
        "source": "n1",
        "target": "n12",
        "relationType": "regulado_por",
        "similarityScore": 0.86,
    },
    {"id": "e6", "source": "n3", "target": "n4", "relationType": "mejora", "similarityScore": 0.92},
    {"id": "e7", "source": "n5", "target": "n6", "relationType": "atrae", "similarityScore": 0.79},
    {"id": "e8", "source": "n5", "target": "n7", "relationType": "genera", "similarityScore": 0.83},
    {
        "id": "e9",
        "source": "n8",
        "target": "n9",
        "relationType": "provoca",
        "similarityScore": 0.76,
    },
    {
        "id": "e10",
        "source": "n10",
        "target": "n8",
        "relationType": "agrava",
        "similarityScore": 0.74,
    },
    {
        "id": "e11",
        "source": "n16",
        "target": "n5",
        "relationType": "sub_mercado",
        "similarityScore": 0.82,
    },
    {
        "id": "e12",
        "source": "n17",
        "target": "n16",
        "relationType": "parte_de",
        "similarityScore": 0.77,
    },
    {
        "id": "e13",
        "source": "n18",
        "target": "n17",
        "relationType": "apoya",
        "similarityScore": 0.71,
    },
    # FINDING → CONCEPT
    {
        "id": "e14",
        "source": "n1",
        "target": "c1",
        "relationType": "related_to",
        "similarityScore": 0.80,
    },
    {
        "id": "e15",
        "source": "n5",
        "target": "c2",
        "relationType": "related_to",
        "similarityScore": 0.76,
    },
    {
        "id": "e16",
        "source": "n12",
        "target": "c3",
        "relationType": "related_to",
        "similarityScore": 0.89,
    },
    # FINDING → SOURCE
    {
        "id": "e17",
        "source": "n3",
        "target": "s1",
        "relationType": "REFERENCES",
        "similarityScore": 0.85,
    },
    {
        "id": "e18",
        "source": "n5",
        "target": "s2",
        "relationType": "REFERENCES",
        "similarityScore": 0.80,
    },
    {
        "id": "e19",
        "source": "n12",
        "target": "s3",
        "relationType": "REFERENCES",
        "similarityScore": 0.93,
    },
    # PATENT ← FINDING (menciona)
    {
        "id": "e20",
        "source": "n2",
        "target": "p2",
        "relationType": "mentions",
        "similarityScore": 0.82,
    },
    {
        "id": "e21",
        "source": "n3",
        "target": "p3",
        "relationType": "mentions",
        "similarityScore": 0.79,
    },
    # COMPANY → PATENT (assigned)
    {
        "id": "e22",
        "source": "co1",
        "target": "p1",
        "relationType": "assigned",
        "similarityScore": 0.90,
    },
    {
        "id": "e23",
        "source": "co1",
        "target": "p3",
        "relationType": "assigned",
        "similarityScore": 0.85,
    },
    {
        "id": "e24",
        "source": "co4",
        "target": "p2",
        "relationType": "assigned",
        "similarityScore": 0.88,
    },
    # COMPANY → FINDING (implementa / menciona)
    {
        "id": "e25",
        "source": "co1",
        "target": "n2",
        "relationType": "implementa",
        "similarityScore": 0.88,
    },
    {
        "id": "e26",
        "source": "co2",
        "target": "n4",
        "relationType": "referencia",
        "similarityScore": 0.84,
    },
    {
        "id": "e27",
        "source": "co3",
        "target": "n10",
        "relationType": "mentions",
        "similarityScore": 0.80,
    },
    {"id": "e28", "source": "co5", "target": "n2", "relationType": "usa", "similarityScore": 0.79},
    # COMPANY emplea PERSON
    {
        "id": "e29",
        "source": "co2",
        "target": "per3",
        "relationType": "employs",
        "similarityScore": 0.95,
    },
    {
        "id": "e30",
        "source": "co1",
        "target": "per2",
        "relationType": "employs",
        "similarityScore": 0.70,
    },
    # PERSON → FINDING / PATENT (authored / invented)
    {
        "id": "e31",
        "source": "per1",
        "target": "n3",
        "relationType": "authored",
        "similarityScore": 0.72,
    },
    {
        "id": "e32",
        "source": "per2",
        "target": "p3",
        "relationType": "invented",
        "similarityScore": 0.75,
    },
    {
        "id": "e33",
        "source": "per3",
        "target": "n1",
        "relationType": "mentions",
        "similarityScore": 0.88,
    },
]

# Ecosistema tecnológico simulado (T041)
MOCK_ECOSYSTEM = {
    "technologies": [
        {
            "name": "Generative AI (LLMs)",
            "category": "NLP/Generación",
            "maturity": 0.75,
            "adoption": 0.65,
            "trend": "rising",
            "keyPlayers": ["OpenAI", "Google DeepMind", "Meta AI"],
        },
        {
            "name": "Digital Twins / Simulación",
            "category": "Simulación",
            "maturity": 0.70,
            "adoption": 0.55,
            "trend": "rising",
            "keyPlayers": ["NVIDIA Omniverse", "Siemens", "Microsoft Azure"],
        },
        {
            "name": "Computer Vision (ViTs)",
            "category": "Visión Artificial",
            "maturity": 0.85,
            "adoption": 0.72,
            "trend": "stable",
            "keyPlayers": ["Meta AI", "Google", "OpenCV"],
        },
        {
            "name": "Edge AI / TinyML",
            "category": "Hardware IA",
            "maturity": 0.50,
            "adoption": 0.30,
            "trend": "emerging",
            "keyPlayers": ["Qualcomm", "ARM", "Syntiant"],
        },
    ],
    "relationships": [
        {"source": "Generative AI (LLMs)", "target": "Digital Twins / Simulación", "type": "complementa"},
        {"source": "Computer Vision (ViTs)", "target": "Edge AI / TinyML", "type": "se_ejecuta_en"},
        {"source": "Digital Twins / Simulación", "target": "Edge AI / TinyML", "type": "requiere"},
    ],
    "maturityLevels": {
        "emerging": {"count": 1, "avgMaturity": 0.50},
        "rising": {"count": 2, "avgMaturity": 0.725},
        "stable": {"count": 1, "avgMaturity": 0.85},
        "declining": {"count": 0, "avgMaturity": 0.0},
    },
}

# ---------------------------------------------------------------------------
# App FastAPI
# ---------------------------------------------------------------------------

app = FastAPI(title="Vigilador Tecnológico 2.0 — Mock Server", version="2.0.0-mock")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def sse_event(event_type: str, data: Any) -> str:
    """Formatea un evento SSE con tipo y payload JSON."""
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.post("/api/v2/research/start")
async def research_start(body: dict):
    return {
        "sessionId": SESSION_ID,
        "status": "CLARIFYING",
        "questions": CLARIFICATION_QUESTIONS,
    }


@app.post("/api/v2/research/{session_id}/clarify")
async def research_clarify(session_id: str, body: dict):
    return {
        "sessionId": session_id,
        "status": "PLANNING",
        "requiresApproval": True,
        "plan": RESEARCH_PLAN,
    }


@app.get("/api/v2/research/{session_id}/plan")
async def research_plan(session_id: str):
    return {"sessionId": session_id, "plan": RESEARCH_PLAN}


@app.post("/api/v2/research/{session_id}/approve")
async def research_approve(session_id: str):
    return {
        "sessionId": session_id,
        "status": "EXECUTING",
        "message": "Investigación iniciada. Conecte al stream SSE para seguir el progreso.",
    }


@app.get("/api/v2/research/{session_id}/stream")
async def research_stream(session_id: str):
    """
    SSE stream con timing realista (~35s total).

    Secuencia de eventos:
      t=0s   → BranchStarted x6 (simultáneo)
      t=2-8s → BranchProgress (iteraciones por rama, escalonadas)
      t=9-12s→ BranchCompleted x6
      t=13s  → AllBranchesCompleted
      t=14s  → FusionStarted
      t=16s  → FusionProgress
      t=18s  → GraphBuildingStarted
      t=20s  → GraphAnalyticsComputed
      t=22s  → ReportGenerated
      t=23s  → ReportVariantsGenerated
    """

    async def event_generator():
        branches = [
            "AVANCES",
            "COMERCIAL",
            "RIESGO",
            "PI_NORMATIVA",
            "COMPETITIVO",
            "OPORTUNIDADES",
        ]

        await asyncio.sleep(0.3)

        # Arrancar todas las ramas
        for branch in branches:
            yield sse_event("BranchStarted", {"branch": branch})
        await asyncio.sleep(0.5)

        # Emitir iteraciones escalonadas por rama. Un delay por paso de
        # BRANCH_ITERATIONS — debe tener al menos tantos elementos como
        # pasos tenga la rama (si no, el paso cae al fallback 1.0s y el
        # ritmo se aplana).
        delays = {
            "AVANCES": [1.0, 1.8, 1.5, 1.6],
            "COMERCIAL": [1.2, 1.6],
            "RIESGO": [1.4, 1.5],
            "PI_NORMATIVA": [1.0, 1.7, 1.5, 1.4, 1.6],
            "COMPETITIVO": [1.3, 1.4, 1.5],
            "OPORTUNIDADES": [1.1, 1.3],
        }

        # Entrelazar iteraciones en orden temporal aproximado
        max_iters = max(len(v) for v in BRANCH_ITERATIONS.values())
        for step_idx in range(max_iters):
            tasks = []
            for branch in branches:
                iters = BRANCH_ITERATIONS.get(branch, [])
                if step_idx < len(iters):
                    branch_delays = delays.get(branch, [1.0] * max_iters)
                    d = branch_delays[step_idx] if step_idx < len(branch_delays) else 1.0
                    tasks.append((d, branch, iters[step_idx]))

            # Ordenar por delay para emitir en orden temporal
            tasks.sort(key=lambda x: x[0])
            accumulated = 0.0
            for delay, branch, iteration in tasks:
                await asyncio.sleep(delay - accumulated)
                accumulated = delay
                yield sse_event("BranchProgress", {"branch": branch, "iteration": iteration})

            # Planner reactivo: tras el primer barrido, una rama detecta un
            # gap y el BranchCoordinator inyecta una directiva a otra rama a
            # mitad de ejecución (gap_detected → ReplanAction → directiva).
            if step_idx == 0:
                await asyncio.sleep(0.4)
                for replan in REPLAN_SIGNALS:
                    yield sse_event("ReplanTriggered", replan)
                    await asyncio.sleep(0.5)

            await asyncio.sleep(0.3)

        await asyncio.sleep(0.5)

        # T054: ~20% de probabilidad de fallo + recuperación en una rama aleatoria
        if random.random() < 0.20:
            failed_branch = random.choice(branches)
            yield sse_event("BranchFailed", {"branch": failed_branch, "reason": "Error en proveedor MCP tavily: timeout excedido (30s)"})
            await asyncio.sleep(0.3)
            yield sse_event("BranchRestarted", {"branch": failed_branch, "reason": "Reintento con proveedor alternativo (exa)"})
            await asyncio.sleep(0.3)

        # Completar ramas
        for branch in branches:
            yield sse_event("BranchCompleted", {"branch": branch})
            await asyncio.sleep(0.15)

        await asyncio.sleep(0.8)
        yield sse_event("AllBranchesCompleted", {"sessionId": session_id})

        await asyncio.sleep(1.0)
        yield sse_event("FusionStarted", {"sessionId": session_id})

        await asyncio.sleep(2.0)
        yield sse_event("FusionProgress", {"sessionId": session_id, "progress": 50})

        await asyncio.sleep(1.5)
        # Nota: El backend real emite 1 FusionProgress (50%). El mock emite 2 para testear la UI.
        yield sse_event("FusionProgress", {"sessionId": session_id, "progress": 100})

        await asyncio.sleep(0.8)
        yield sse_event("GraphBuildingStarted", {"sessionId": session_id})

        await asyncio.sleep(2.0)
        yield sse_event("GraphAnalyticsComputed", {"sessionId": session_id})

        await asyncio.sleep(1.5)

        report = {**FINAL_REPORT, "sessionId": session_id}
        yield sse_event("ReportGenerated", {"report": report})

        await asyncio.sleep(0.5)
        yield sse_event("ReportVariantsGenerated", {"types": ["markdown", "html"]})

        await asyncio.sleep(0.4)
        # T055: EvaluationComputed con KPIs de todas las ramas
        yield sse_event("EvaluationComputed", {
            "sessionId": session_id,
            "evaluations": [
                {"branchType": "AVANCES", "coverageKpi": 0.91, "precisionKpi": 0.87, "latencyMsKpi": 4320},
                {"branchType": "COMERCIAL", "coverageKpi": 0.83, "precisionKpi": 0.79, "latencyMsKpi": 3840},
                {"branchType": "RIESGO", "coverageKpi": 0.88, "precisionKpi": 0.85, "latencyMsKpi": 4100},
                {"branchType": "PI_NORMATIVA", "coverageKpi": 0.94, "precisionKpi": 0.91, "latencyMsKpi": 3650},
                {"branchType": "COMPETITIVO", "coverageKpi": 0.86, "precisionKpi": 0.83, "latencyMsKpi": 3920},
                {"branchType": "OPORTUNIDADES", "coverageKpi": 0.79, "precisionKpi": 0.76, "latencyMsKpi": 3510},
            ],
        })

        # Mantener conexión abierta brevemente y luego cerrar
        await asyncio.sleep(2.0)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/v2/research/{session_id}/report")
async def research_report(session_id: str):
    return {**FINAL_REPORT, "sessionId": session_id}


@app.get("/api/v2/research/{session_id}/sources")
async def research_sources(session_id: str):
    return {
        "sessionId": session_id,
        "total": len(SOURCES),
        "items": SOURCES,
    }


@app.get("/api/v2/research/{session_id}/graph")
async def research_graph(session_id: str):
    return {
        "sessionId": session_id,
        "nodes": GRAPH_NODES,
        "edges": GRAPH_EDGES,
    }


@app.get("/api/v2/research/{session_id}/graph/analytics")
async def research_graph_analytics(session_id: str):
    return {
        "sessionId": session_id,
        "centralNodes": [n["id"] for n in sorted(GRAPH_NODES, key=lambda x: -x["centrality"])[:5]],
        "clusters": [
            {"id": "cl1", "label": "Avances Técnicos", "nodeIds": ["n1", "n2", "n3", "n4", "c1"]},
            {"id": "cl2", "label": "Mercado y Comercial", "nodeIds": ["n5", "n6", "n7", "c2"]},
            {"id": "cl3", "label": "Riesgos", "nodeIds": ["n8", "n9", "n10"]},
            {"id": "cl4", "label": "Regulatorio / PI", "nodeIds": ["n12", "c3", "p1", "p2", "p3"]},
            {
                "id": "cl5",
                "label": "Panorama Competitivo",
                "nodeIds": ["co1", "co2", "co3", "co4", "co5", "per3"],
            },
            {"id": "cl6", "label": "Oportunidades", "nodeIds": ["n16", "n17", "n18"]},
        ],
        "density": 0.134,
        "avgPathLength": 2.47,
        "clusteringCoefficient": 0.412,
    }


@app.get("/api/v2/research/{session_id}/graph/search")
async def research_graph_search(session_id: str, query: str = ""):
    q = query.lower()
    results = [
        {"nodeId": n["id"], "label": n["label"], "score": n["centrality"]}
        for n in GRAPH_NODES
        if q in n["label"].lower()
    ]
    return {"items": results}


@app.get("/api/v2/research/{session_id}/graph/path")
async def research_graph_path(session_id: str, sourceNodeId: str, targetNodeId: str):
    return {
        "nodeIds": [sourceNodeId, "n1", targetNodeId],
        "edgeIds": ["e1", "e4"],
        "totalCost": 0.42,
    }


@app.get("/api/v2/research/{session_id}/providers")
async def research_providers(session_id: str):
    # T052: Nota: branchKpis, confidenceCalibration y campos agregados son
    # extensión del mock para desarrollo frontend — el backend real no los
    # incluye en este endpoint.
    return {
        "sessionId": session_id,
        "providers": [
            {"name": "tavily", "avgLatencyMs": 843, "errorRate": 0.02, "retryRate": 0.03},
            {"name": "arxiv", "avgLatencyMs": 612, "errorRate": 0.01, "retryRate": 0.01},
            {"name": "google_scholar", "avgLatencyMs": 1120, "errorRate": 0.04, "retryRate": 0.05},
            {"name": "exa", "avgLatencyMs": 754, "errorRate": 0.02, "retryRate": 0.02},
            {"name": "brave", "avgLatencyMs": 523, "errorRate": 0.01, "retryRate": 0.01},
            {"name": "fetch", "avgLatencyMs": 389, "errorRate": 0.00, "retryRate": 0.00},
            {"name": "serper", "avgLatencyMs": 671, "errorRate": 0.03, "retryRate": 0.03},
        ],
        "branchKpis": [
            {
                "branchType": "AVANCES",
                "coverageKpi": 0.91,
                "precisionKpi": 0.87,
                "latencyMsKpi": 4320,
            },
            {
                "branchType": "COMERCIAL",
                "coverageKpi": 0.83,
                "precisionKpi": 0.79,
                "latencyMsKpi": 3840,
            },
            {
                "branchType": "RIESGO",
                "coverageKpi": 0.88,
                "precisionKpi": 0.85,
                "latencyMsKpi": 4100,
            },
            {
                "branchType": "PI_NORMATIVA",
                "coverageKpi": 0.94,
                "precisionKpi": 0.91,
                "latencyMsKpi": 3650,
            },
            {
                "branchType": "COMPETITIVO",
                "coverageKpi": 0.86,
                "precisionKpi": 0.83,
                "latencyMsKpi": 3920,
            },
            {
                "branchType": "OPORTUNIDADES",
                "coverageKpi": 0.79,
                "precisionKpi": 0.76,
                "latencyMsKpi": 3510,
            },
        ],
        "confidenceScore": 0.847,
        "totalSources": 12,
        "totalFindings": 28,
        # ConfidenceCalibrator: por bucket [0-0.2..0.8-1.0], confianza media
        # predicha por los prompts vs tasa real de acierto observada. factor
        # = real/predicho aplicado para corregir el sesgo del modelo.
        "confidenceCalibration": [
            {"bucket": "0.6-0.8", "predicted": 0.71, "observed": 0.64, "samples": 23, "factor": 0.90},
            {"bucket": "0.8-1.0", "predicted": 0.90, "observed": 0.86, "samples": 41, "factor": 0.96},
            {"bucket": "0.4-0.6", "predicted": 0.52, "observed": 0.55, "samples": 12, "factor": 1.06},
        ],
    }


@app.delete("/api/v2/research/{session_id}")
async def research_delete(session_id: str):
    return {"status": "deleted", "sessionId": session_id}


@app.post("/api/v2/sessions/{session_id}/ask")
async def session_ask(session_id: str, body: dict):
    query = body.get("query", "")
    return {
        "answer": (
            f"Basándome en los hallazgos de la investigación sobre '{QUERY_EJEMPLO}': "
            f"Con respecto a '{query}', el análisis identificó que los líderes del sector "
            f"están convergiendo hacia soluciones integradas que combinan IA generativa con "
            f"gemelos digitales. La confianza en esta respuesta es 0.82, derivada principalmente "
            f"de las ramas AVANCES y COMPETITIVO."
        ),
        "sources": [SOURCES[0]["id"], SOURCES[2]["id"]],
        "requiresPermission": False,
    }


@app.delete("/api/v2/sessions/{session_id}/conversation")
async def session_end_conversation(session_id: str):
    return {"status": "closed"}


@app.get("/api/v2/sessions/timeline")
async def sessions_timeline():
    return {
        "sessions": [
            {
                "sessionId": SESSION_ID,
                "querySummary": QUERY_EJEMPLO,
                "timestamp": datetime.now(UTC).isoformat(),
                "entities": [
                    n["label"] for n in GRAPH_NODES if n["nodeType"] in ("PERSON", "COMPANY")
                ],
                "findingCount": 28,
            }
        ]
    }


@app.get("/api/v2/reports/{report_id}/export")
async def report_export(report_id: str, format: str = "md"):
    content = FINAL_REPORT["markdown"]
    if format == "html":
        content = f"<html><body><pre>{content}</pre></body></html>"
    return {"content": content, "format": format, "reportId": report_id}


@app.patch("/api/v2/sources/{source_id}/score")
async def source_score(source_id: str, body: dict):
    delta = body.get("delta", 0)
    return {
        "sourceId": source_id,
        "newScore": 75 + delta,
        "adjustment": delta,
        "reason": body.get("reason", ""),
    }


@app.post("/api/v2/upload/document")
async def upload_document():
    return {
        "markdown": "# Documento cargado\n\nContenido simulado del documento procesado.",
        "format": "pdf",
        "filename": "documento.pdf",
    }


# ---------------------------------------------------------------------------
# Endpoints nuevos (T037–T055)
# ---------------------------------------------------------------------------


@app.get("/api/v2/research/{session_id}/graph/nodes")
async def research_graph_nodes(session_id: str):
    """T037: Devuelve solo los nodos del grafo."""
    return {"sessionId": session_id, "total": len(GRAPH_NODES), "items": GRAPH_NODES}


@app.get("/api/v2/research/{session_id}/graph/edges")
async def research_graph_edges(session_id: str):
    """T038: Devuelve solo las aristas del grafo."""
    return {"sessionId": session_id, "total": len(GRAPH_EDGES), "items": GRAPH_EDGES}


@app.get("/api/v2/research/{session_id}/graph/{node_id}/sources")
async def research_graph_node_sources(session_id: str, node_id: str):
    """T039: Devuelve los IDs de las fuentes de un nodo específico."""
    matched = [n for n in GRAPH_NODES if n["id"] == node_id]
    source_ids = matched[0].get("sourceIds", []) if matched else []
    return {"sessionId": session_id, "nodeId": node_id, "sourceNodeIds": source_ids}


@app.post("/api/v2/research/{session_id}/modify")
async def research_modify(session_id: str, body: dict):
    """T040: Simula modificación del plan de investigación."""
    return {
        "sessionId": session_id,
        "status": "PLANNING",
        "message": "Plan modificado exitosamente.",
        "plan": RESEARCH_PLAN,
    }


@app.get("/api/v2/research/{session_id}/graph/ecosystem")
async def research_graph_ecosystem(session_id: str, seed: str = "", depth: int = 2):
    """T041: Simula descubrimiento de ecosistema tecnológico."""
    return {"sessionId": session_id, "ecosystem": MOCK_ECOSYSTEM, "seed": seed, "depth": depth}


@app.get("/api/v2/research/{session_id}/graph/search-cross-session")
async def research_graph_search_cross_session(session_id: str, query: str = "", limit: int = 10):
    """T042: Simula búsqueda cross-session."""
    return {
        "sessionId": session_id,
        "query": query,
        "limit": limit,
        "results": [
            {
                "sessionId": "prev-session-001",
                "querySummary": "Blockchain en cadena de suministro automotriz",
                "timestamp": "2026-03-10T14:00:00Z",
                "matchedNodes": [n["id"] for n in GRAPH_NODES if query.lower() in n["label"].lower()],
                "relevanceScore": 0.78,
            },
            {
                "sessionId": "prev-session-002",
                "querySummary": "IoT industrial para mantenimiento predictivo",
                "timestamp": "2026-01-22T09:30:00Z",
                "matchedNodes": [],
                "relevanceScore": 0.65,
            },
            {
                "sessionId": "prev-session-003",
                "querySummary": "Gemelos digitales en manufactura automotriz",
                "timestamp": "2025-11-05T16:45:00Z",
                "matchedNodes": ["n2", "n1"],
                "relevanceScore": 0.91,
            },
        ],
    }


@app.post("/api/v2/research/{session_id}/decision")
async def research_decision(session_id: str, body: dict):
    """T043: Simula análisis de decisión."""
    question = body.get("question", "")
    return {
        "sessionId": session_id,
        "question": question,
        "decision": {
            "recommendedOption": "Inversión en IA para control de calidad",
            "scores": {
                "Integración gemelos digitales": 0.87,
                "Plataforma SaaS inspección visual": 0.82,
                "Consultoría adopción Tier-2/3": 0.74,
            },
            "confidence": 0.82,
            "rationale": "La opción recomendada maximiza el ROI en el horizonte 2-3 años "
            "alineándose con la madurez tecnológica actual del mercado.",
        },
    }


@app.post("/api/v2/research/{session_id}/obsolescence")
async def research_obsolescence(session_id: str, body: dict):
    """T050: Simula análisis de obsolescencia tecnológica."""
    tech = body.get("tech", "Computer Vision")
    risk = random.choice(["alta", "media", "baja"])
    lifespan = random.choice(["2-3 years", "3-5 years", "5-8 years"])
    results = [{
        "technology": tech,
        "obsolescenceRisk": risk,
        "estimatedLifespan": lifespan,
        "replacementTrends": [
            "Modelos fundacionales multimodales",
            "Arquitecturas neuronales eficientes en edge",
        ],
    }]
    return {"sessionId": session_id, "results": results}


@app.post("/api/v2/research/{session_id}/hype-analysis")
async def research_hype_analysis(session_id: str, body: dict):
    """T051: Simula análisis de ciclo de hype."""
    tech = body.get("tech", "")
    return {
        "sessionId": session_id,
        "tech": tech,
        "hypeCycle": {
            "phase": "Trough of Disillusionment",
            "peakYear": 2026,
            "maturityHorizon": "2-5 years",
            "technologies": [
                {"name": "Generative AI for Manufacturing", "phase": "Peak of Inflated Expectations", "visibility": 0.85, "maturity": 0.30},
                {"name": "Digital Twins", "phase": "Slope of Enlightenment", "visibility": 0.72, "maturity": 0.65},
                {"name": "Edge AI / TinyML", "phase": "Innovation Trigger", "visibility": 0.40, "maturity": 0.15},
                {"name": "Computer Vision QC", "phase": "Plateau of Productivity", "visibility": 0.60, "maturity": 0.88},
            ],
        },
    }


# ---------------------------------------------------------------------------
# Punto de entrada
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("  Vigilador Tecnológico 2.0 — Mock Server")
    print("=" * 60)
    print("  URL base API : http://localhost:8000/api/v2")
    print(f"  Tema demo    : {QUERY_EJEMPLO}")
    print(f"  Session ID   : {SESSION_ID}")
    print()
    print("  Flujo de prueba:")
    print("   1. Abre el frontend (npm run dev en frontend/)")
    print("   2. Escribe cualquier consulta en el chat")
    print("   3. Responde las 3 preguntas de aclaración")
    print("   4. Aprueba el plan de investigación")
    print("   5. Observa el progreso en tiempo real (~35s)")
    print("   6. Explora el reporte, grafo y métricas")
    print("=" * 60)

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
