"""Mock data for research plan, sources, report, graph.

Branch iterations, replan signals and cross-session helpers are in
mock_server.data.branches.
"""

import uuid
from datetime import UTC, datetime

from mock_server.data.branches import BRANCH_ITERATIONS, REPLAN_SIGNALS, CROSS_SESSION_RECURRING, _delta_focus

SESSION_ID = str(uuid.uuid4())

QUERY_EJEMPLO = "IA generativa en manufactura automotriz"

CLARIFICATION_QUESTIONS = [
    {"id": "q1", "text": "¿El análisis debe enfocarse en fabricantes OEM, proveedores Tier-1, o ambos?"},
    {"id": "q2", "text": "¿Qué región geográfica tiene mayor prioridad: América del Norte, Europa, Asia-Pacífico, o global?"},
    {"id": "q3", "text": "¿El horizonte temporal de interés es corto plazo (1-2 años), mediano (3-5 años), o largo plazo (+5 años)?"},
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

SOURCES = [
    {"id": str(uuid.uuid4()), "url": "https://arxiv.org/abs/2401.12345", "title": "Generative AI for Automotive Quality Control: A Systematic Review", "provider": "arxiv", "branchType": "AVANCES", "accessedAt": "2026-05-16T10:00:00Z"},
    {"id": str(uuid.uuid4()), "url": "https://scholar.google.com/paper/ViT-automotive", "title": "Vision Transformers Outperform CNNs in Weld Defect Detection", "provider": "google_scholar", "branchType": "AVANCES", "accessedAt": "2026-05-16T10:01:00Z"},
    {"id": str(uuid.uuid4()), "url": "https://www.marketsandmarkets.com/ai-automotive-2024", "title": "AI in Automotive Manufacturing Market Report 2024-2030", "provider": "tavily", "branchType": "COMERCIAL", "accessedAt": "2026-05-16T10:02:00Z"},
    {"id": str(uuid.uuid4()), "url": "https://techcrunch.com/2024/ai-automotive-funding", "title": "AI Automotive Startups Raise Record $2.1B in H1 2024", "provider": "exa", "branchType": "COMERCIAL", "accessedAt": "2026-05-16T10:03:00Z"},
    {"id": str(uuid.uuid4()), "url": "https://www.dragos.com/ot-security-automotive-2024", "title": "OT Cybersecurity in Connected Automotive Plants", "provider": "tavily", "branchType": "RIESGO", "accessedAt": "2026-05-16T10:04:00Z"},
    {"id": str(uuid.uuid4()), "url": "https://www.iso.org/standard/ai-manufacturing-2024", "title": "ISO/IEC 42001 AI Management Systems for Manufacturing", "provider": "fetch", "branchType": "PI_NORMATIVA", "accessedAt": "2026-05-16T10:05:00Z"},
    {"id": str(uuid.uuid4()), "url": "https://eur-lex.europa.eu/ai-act-automotive", "title": "EU AI Act Impact Assessment: Automotive Manufacturing", "provider": "fetch", "branchType": "PI_NORMATIVA", "accessedAt": "2026-05-16T10:06:00Z"},
    {"id": str(uuid.uuid4()), "url": "https://www.toyota-global.com/tps-ai-strategy", "title": "Toyota Production System AI: $800M Investment Plan", "provider": "tavily", "branchType": "COMPETITIVO", "accessedAt": "2026-05-16T10:07:00Z"},
    {"id": str(uuid.uuid4()), "url": "https://electrek.co/2024/tesla-gigafactory-ai", "title": "Tesla Gigafactory: AI-Driven 40-Second Vehicle Cycle", "provider": "exa", "branchType": "COMPETITIVO", "accessedAt": "2026-05-16T10:08:00Z"},
    {"id": str(uuid.uuid4()), "url": "https://www.ifc.org/ai-automotive-latam-2024", "title": "AI Adoption in LatAm Automotive: Mexico and India Emerge", "provider": "brave", "branchType": "OPORTUNIDADES", "accessedAt": "2026-05-16T10:09:00Z"},
    {"id": str(uuid.uuid4()), "url": "https://www.mckinsey.com/ai-tier2-automotive", "title": "The $6.8B Opportunity: AI for Tier-2/3 Automotive Suppliers", "provider": "tavily", "branchType": "OPORTUNIDADES", "accessedAt": "2026-05-16T10:10:00Z"},
    {"id": str(uuid.uuid4()), "url": "https://patents.google.com/toyota-ai-manufacturing", "title": "Toyota AI Manufacturing Patent Portfolio Analysis 2024", "provider": "google_scholar", "branchType": "PI_NORMATIVA", "accessedAt": "2026-05-16T10:11:00Z"},
]

FINAL_REPORT = {
    "sessionId": SESSION_ID,
    "executiveSummary": "La IA generativa está transformando fundamentalmente la manufactura automotriz a escala global. Con un mercado valorado en **$4.2B en 2024** y una tasa de crecimiento anual del 28.3%, el sector alcanzará los $18.7B en 2030. Los líderes del mercado —Toyota, Tesla y BMW— han comprometido inversiones superiores a los $1.5B combinados en los próximos 3 años. Sin embargo, el 78% de proveedores Tier-2 y Tier-3 permanecen sin adoptar estas tecnologías, creando una ventana de oportunidad estimada en $6.8B para integradores tecnológicos especializados.",
    "technicalSection": "## Avances Técnicos\n\n### Modelos de Lenguaje en Líneas de Ensamblaje\nLos LLMs se están desplegando para optimización de secuencias de ensamblaje, detección de anomalías en tiempo real y generación automática de instrucciones de trabajo. BMW y Toyota lideran con pilotos en producción que reportan reducciones del 23% en tiempo de ciclo y 31% menos defectos escapados.\n\n### Visión Computacional de Nueva Generación\nLos modelos Vision Transformer (ViT) han superado a las CNN clásicas en detección de microfisuras en soldadura, con tasas de detección superiores al 97.3%. NVIDIA Omniverse Industrial y Siemens lideran la integración con gemelos digitales para simulación predictiva de fallos.\n\n### Gemelos Digitales + IA Generativa\nLa convergencia entre gemelos digitales y modelos generativos permite simular millones de escenarios de producción antes de implementar cambios en línea.",
    "commercialSection": "## Análisis Comercial\n\n### Dinámica de Mercado\nEl mercado global de IA en manufactura automotriz alcanzó $4.2B en 2024 (CAGR: 28.3%). Norteamérica concentra el 38% del mercado, seguida de Europa (31%) y Asia-Pacífico (27%).\n\n### Flujos de Inversión\nH1 2024 registró un récord de $2.1B en inversión en startups especializadas.\n\n### Retorno de Inversión\nLas implementaciones maduras reportan ROI promedio de 340% en 3 años.",
    "riskSection": "## Análisis de Riesgos\n\n### Riesgos de Ciberseguridad (Crítico)\nEl 67% de fabricantes automotrices reportó intentos de intrusión en sistemas OT conectados a IA en 2023.\n\n### Riesgo de Fallos en Producción (Alto)\nIdentificados 6 incidentes documentados donde modelos IA produjeron inferencias incorrectas bajo condiciones de iluminación no estándar.\n\n### Dependencia de Proveedores (Moderado)\nAlta concentración en NVIDIA (chips), Microsoft Azure (infraestructura cloud).",
    "crossAnalysis": "## Análisis Cruzado\n\nLa convergencia de los hallazgos de las seis ramas revela tres patrones estructurales:\n1. Brecha de Adopción como Oportunidad Estratégica\n2. Tensión Regulatoria-Competitiva\n3. Consolidación Patentaria como Barrera de Entrada",
    "recommendations": [
        {"text": "Desarrollar una plataforma de inspección visual IA específica para proveedores Tier-2/3 con modelo de negocio SaaS.", "priority": "alta", "basedOn": ["COMERCIAL", "OPORTUNIDADES"]},
        {"text": "Incorporar marcos de seguridad OT (IEC 62443) como diferenciador competitivo.", "priority": "alta", "basedOn": ["RIESGO", "COMPETITIVO"]},
        {"text": "Priorizar cumplimiento anticipado del EU AI Act antes de 2026.", "priority": "media", "basedOn": ["PI_NORMATIVA", "COMERCIAL"]},
        {"text": "Explorar colaboraciones con universidades en México e India.", "priority": "media", "basedOn": ["OPORTUNIDADES", "COMPETITIVO"]},
        {"text": "Implementar estrategia de propiedad intelectual defensiva.", "priority": "baja", "basedOn": ["PI_NORMATIVA", "AVANCES"]},
    ],
    "totalSourcesConsulted": 12,
    "totalLearnings": 28,
    "confidenceScore": 0.847,
    "generatedAt": datetime.now(UTC).isoformat(),
}

INTELLIGENCE_SECTIONS = "\n\n".join([
    "\n".join([
        "## Madurez tecnológica",
        "",
        "Nivel de madurez tecnológica (TRL) estimado para cada tecnología detectada en la investigación:",
        "",
        "### Visión Computacional / Vision Transformers",
        "- **TRL 7-9 · comercialización**",
        "- 9 empresas y 6 patentes frente a 4 papers: los modelos ViT para detección de defectos están desplegados en líneas de producción de Toyota y BMW. Tecnología en comercialización activa.",
        "",
        "### Gemelos Digitales de Manufactura",
        "- **TRL 7-9 · comercialización**",
        "- NVIDIA Omniverse y Siemens ofrecen plataformas comerciales de gemelos digitales integradas con IA generativa. 7 empresas con producto frente a 3 papers: madurez comercial.",
        "",
        "### Edge AI para Inspección",
        "- **TRL 4-6 · validación y prototipos**",
        "- 5 prototipos y pilotos en entornos controlados frente a 4 papers académicos: la inferencia en el borde para inspección de calidad está en validación, aún sin despliegue masivo.",
        "",
        "### Quantum Machine Learning",
        "- **TRL 1-3 · investigación básica**",
        "- 8 papers académicos dominan (89% de las señales) con escasa tracción comercial: el ML cuántico aplicado a manufactura sigue en investigación básica, sin prototipos productivos.",
    ]),
    "## Hallazgos priorizados por impacto\n- `0.871` **vision-defect-detection** — Detección de defectos por visión alcanza 99.2% de precisión en líneas de Toyota (autoridad 0.95, novedad 0.92, convergencia 0.85)\n- `0.764` **predictive-maintenance** — Mantenimiento predictivo reduce paradas no planificadas 38% en plantas Bosch\n- `0.612` **digital-twin-roi** — Gemelos digitales con ROI de 340% en 3 años",
    "## Puntos en disputa\n\n### digital-twin-roi\n- **A** (conf. 0.85): Los gemelos digitales reducen el time-to-market 31% según Stellantis\n- **B** (conf. 0.60): Los gemelos digitales no muestran ROI medible en plantas de menos de 500 empleados\n- _Las fuentes difieren en polaridad sobre un tema compartido; revisar evidencia antes de concluir._",
    "## Señales débiles emergentes\n\n- **neuromorphic-inspection** — Emergente: 2 menciones en 2 rama(s).\n- **federated-quality-models** — Emergente: 3 menciones en 2 rama(s).\n- **edge-llm-orchestration** — Emergente: 2 menciones en 2 rama(s).",
    "## Trayectoria causal\n\n- **2021** (research) → **2023** (prototype): research → prototype\n- **2023** (prototype) → **2024** (funding): prototype → funding\n- **2024** (funding) → **2026** (market): funding → market",
    "## Verificación adversarial\n\nEl control automático detectó 2 debilidad(es):\n- **[unsourced_finding]** Finding sin fuente: «La adopción de IA en Tier-2 supera el 40% en 2025»\n- **[unsupported_recommendation]** Recomendación sin respaldo: «Priorizar alianzas con fabricantes de chips neuromórficos»",
    "## Visualizaciones generadas\n\n### Proyección de publicaciones IA manufactura 2018–2027\n![Gráfico de tendencia bibliométrica generado por agente AVANCES](/charts/trend-bibliometric.png)\nAnálisis de regresión lineal sobre datos OpenAlex (r=0.987, p<0.01). La tendencia muestra un crecimiento sostenido del **41% anual**, con proyección de 2.456 publicaciones en 2025 y 3.740 en 2027. El elevado coeficiente de correlación confirma que el crecimiento no es ruido estadístico sino una tendencia estructural en el campo.",
])

FINAL_REPORT["markdown"] = "\n\n".join([
    f"# Informe: {QUERY_EJEMPLO}",
    f"## Resumen Ejecutivo\n{FINAL_REPORT['executiveSummary']}",
    FINAL_REPORT["technicalSection"],
    FINAL_REPORT["commercialSection"],
    FINAL_REPORT["riskSection"],
    FINAL_REPORT["crossAnalysis"],
    "## Recomendaciones\n" + "\n".join(f"- **[{r['priority'].upper()}]** {r['text']}" for r in FINAL_REPORT["recommendations"]),
    INTELLIGENCE_SECTIONS,
])

GRAPH_NODES = [
    {"id": "n1", "nodeType": "TECHNOLOGY", "label": "IA Generativa en Manufactura", "centrality": 0.95, "branchType": "AVANCES", "sourceIds": [], "confidence": 0.92},
    {"id": "n2", "nodeType": "FINDING", "label": "Gemelos Digitales", "centrality": 0.82, "branchType": "AVANCES", "sourceIds": [], "confidence": 0.88},
    {"id": "n3", "nodeType": "FINDING", "label": "Visión Computacional / ViT", "centrality": 0.78, "branchType": "AVANCES", "sourceIds": [], "confidence": 0.91},
    {"id": "n4", "nodeType": "FINDING", "label": "Control de Calidad Automatizado", "centrality": 0.75, "branchType": "AVANCES", "sourceIds": [], "confidence": 0.89},
    {"id": "n5", "nodeType": "FINDING", "label": "Mercado $4.2B (CAGR 28.3%)", "centrality": 0.88, "branchType": "COMERCIAL", "sourceIds": [], "confidence": 0.85},
    {"id": "n6", "nodeType": "FINDING", "label": "Inversión $2.1B H1 2024", "centrality": 0.72, "branchType": "COMERCIAL", "sourceIds": [], "confidence": 0.79},
    {"id": "n7", "nodeType": "FINDING", "label": "ROI 340% en 3 años", "centrality": 0.68, "branchType": "COMERCIAL", "sourceIds": [], "confidence": 0.81},
    {"id": "n8", "nodeType": "FINDING", "label": "Ciberseguridad OT/IT", "centrality": 0.84, "branchType": "RIESGO", "sourceIds": [], "confidence": 0.87},
    {"id": "n9", "nodeType": "FINDING", "label": "Fallos IA en Producción", "centrality": 0.71, "branchType": "RIESGO", "sourceIds": [], "confidence": 0.83},
    {"id": "n10", "nodeType": "FINDING", "label": "Dependencia NVIDIA / Azure", "centrality": 0.65, "branchType": "RIESGO", "sourceIds": [], "confidence": 0.76},
    {"id": "n12", "nodeType": "FINDING", "label": "EU AI Act (2026)", "centrality": 0.86, "branchType": "PI_NORMATIVA", "sourceIds": [], "confidence": 0.93},
    {"id": "n16", "nodeType": "FINDING", "label": "Brecha Tier-2/3 ($6.8B)", "centrality": 0.90, "branchType": "OPORTUNIDADES", "sourceIds": [], "confidence": 0.81},
    {"id": "n17", "nodeType": "FINDING", "label": "Mercados México e India", "centrality": 0.70, "branchType": "OPORTUNIDADES", "sourceIds": [], "confidence": 0.77},
    {"id": "n18", "nodeType": "FINDING", "label": "Colaboración Universidad-OEM", "centrality": 0.62, "branchType": "OPORTUNIDADES", "sourceIds": [], "confidence": 0.73},
    {"id": "c1", "nodeType": "CONCEPT", "label": "Automatización Industrial", "centrality": 0.74, "branchType": "AVANCES", "sourceIds": [], "confidence": 0.85},
    {"id": "c2", "nodeType": "CONCEPT", "label": "Cadena de Suministro", "centrality": 0.66, "branchType": "COMERCIAL", "sourceIds": [], "confidence": 0.78},
    {"id": "c3", "nodeType": "CONCEPT", "label": "Regulación IA", "centrality": 0.72, "branchType": "PI_NORMATIVA", "sourceIds": [], "confidence": 0.88},
    {"id": "p1", "nodeType": "PATENT", "label": "US20230412811 — AI Assembly QC", "centrality": 0.80, "branchType": "PI_NORMATIVA", "sourceIds": [], "confidence": 0.90},
    {"id": "p2", "nodeType": "PATENT", "label": "EP4123456 — Digital Twin Mfg", "centrality": 0.71, "branchType": "PI_NORMATIVA", "sourceIds": [], "confidence": 0.86},
    {"id": "p3", "nodeType": "PATENT", "label": "JP2024081234 — ViT Weld Detect", "centrality": 0.65, "branchType": "PI_NORMATIVA", "sourceIds": [], "confidence": 0.83},
    {"id": "s1", "nodeType": "SOURCE", "label": "arxiv.org/abs/2401.12345", "centrality": 0.55, "branchType": "AVANCES", "sourceIds": [], "confidence": 0.80},
    {"id": "s2", "nodeType": "SOURCE", "label": "marketsandmarkets.com/ai-auto", "centrality": 0.50, "branchType": "COMERCIAL", "sourceIds": [], "confidence": 0.75},
    {"id": "s3", "nodeType": "SOURCE", "label": "eur-lex.europa.eu/ai-act", "centrality": 0.58, "branchType": "PI_NORMATIVA", "sourceIds": [], "confidence": 0.92},
    {"id": "per1", "nodeType": "PERSON", "label": "Raj Reddy", "centrality": 0.60, "branchType": "AVANCES", "sourceIds": [], "confidence": 0.72},
    {"id": "per2", "nodeType": "PERSON", "label": "Akira Yoshino", "centrality": 0.58, "branchType": "PI_NORMATIVA", "sourceIds": [], "confidence": 0.70},
    {"id": "per3", "nodeType": "PERSON", "label": "Elon Musk", "centrality": 0.75, "branchType": "COMPETITIVO", "sourceIds": [], "confidence": 0.95},
    {"id": "co1", "nodeType": "COMPANY", "label": "Toyota", "centrality": 0.85, "branchType": "COMPETITIVO", "sourceIds": [], "confidence": 0.90},
    {"id": "co2", "nodeType": "COMPANY", "label": "Tesla", "centrality": 0.83, "branchType": "COMPETITIVO", "sourceIds": [], "confidence": 0.92},
    {"id": "co3", "nodeType": "COMPANY", "label": "NVIDIA", "centrality": 0.79, "branchType": "COMPETITIVO", "sourceIds": [], "confidence": 0.88},
    {"id": "co4", "nodeType": "COMPANY", "label": "Bosch", "centrality": 0.73, "branchType": "COMPETITIVO", "sourceIds": [], "confidence": 0.85},
    {"id": "co5", "nodeType": "COMPANY", "label": "BMW", "centrality": 0.74, "branchType": "COMPETITIVO", "sourceIds": [], "confidence": 0.84},
]

_NODE_SOURCE_MAP = {"n1": [0, 1], "n2": [0], "n3": [1], "n4": [1], "n5": [2], "n6": [3], "n7": [2], "n8": [4], "n9": [4], "n10": [4], "n12": [5, 6], "n16": [10], "n17": [9], "n18": [9], "p1": [10], "p2": [10], "p3": [1], "s1": [0], "s2": [2], "s3": [6], "co1": [7], "co2": [8], "co3": [8], "co4": [4], "co5": [7], "per1": [1], "per2": [10], "per3": [8]}
for _node in GRAPH_NODES:
    _idxs = _NODE_SOURCE_MAP.get(_node["id"], [])
    _node["sourceIds"] = [SOURCES[i]["id"] for i in _idxs if i < len(SOURCES)]

GRAPH_EDGES = [
    {"id": "e1", "source": "n1", "target": "n2", "relationType": "habilita", "similarityScore": 0.88},
    {"id": "e2", "source": "n1", "target": "n3", "relationType": "incluye", "similarityScore": 0.85},
    {"id": "e3", "source": "n1", "target": "n5", "relationType": "impulsa", "similarityScore": 0.87},
    {"id": "e4", "source": "n1", "target": "n8", "relationType": "expone_a", "similarityScore": 0.81},
    {"id": "e5", "source": "n1", "target": "n12", "relationType": "regulado_por", "similarityScore": 0.86},
    {"id": "e6", "source": "n3", "target": "n4", "relationType": "mejora", "similarityScore": 0.92},
    {"id": "e7", "source": "n5", "target": "n6", "relationType": "atrae", "similarityScore": 0.79},
    {"id": "e8", "source": "n5", "target": "n7", "relationType": "genera", "similarityScore": 0.83},
    {"id": "e9", "source": "n8", "target": "n9", "relationType": "provoca", "similarityScore": 0.76},
    {"id": "e10", "source": "n10", "target": "n8", "relationType": "agrava", "similarityScore": 0.74},
    {"id": "e11", "source": "n16", "target": "n5", "relationType": "sub_mercado", "similarityScore": 0.82},
    {"id": "e12", "source": "n17", "target": "n16", "relationType": "parte_de", "similarityScore": 0.77},
    {"id": "e13", "source": "n18", "target": "n17", "relationType": "apoya", "similarityScore": 0.71},
    {"id": "e14", "source": "n1", "target": "c1", "relationType": "related_to", "similarityScore": 0.80},
    {"id": "e15", "source": "n5", "target": "c2", "relationType": "related_to", "similarityScore": 0.76},
    {"id": "e16", "source": "n12", "target": "c3", "relationType": "related_to", "similarityScore": 0.89},
    {"id": "e17", "source": "n3", "target": "s1", "relationType": "REFERENCES", "similarityScore": 0.85},
    {"id": "e18", "source": "n5", "target": "s2", "relationType": "REFERENCES", "similarityScore": 0.80},
    {"id": "e19", "source": "n12", "target": "s3", "relationType": "REFERENCES", "similarityScore": 0.93},
    {"id": "e20", "source": "n2", "target": "p2", "relationType": "mentions", "similarityScore": 0.82},
    {"id": "e21", "source": "n3", "target": "p3", "relationType": "mentions", "similarityScore": 0.79},
    {"id": "e22", "source": "co1", "target": "p1", "relationType": "assigned", "similarityScore": 0.90},
    {"id": "e23", "source": "co1", "target": "p3", "relationType": "assigned", "similarityScore": 0.85},
    {"id": "e24", "source": "co4", "target": "p2", "relationType": "assigned", "similarityScore": 0.88},
    {"id": "e25", "source": "co1", "target": "n2", "relationType": "implementa", "similarityScore": 0.88},
    {"id": "e26", "source": "co2", "target": "n4", "relationType": "referencia", "similarityScore": 0.84},
    {"id": "e27", "source": "co3", "target": "n10", "relationType": "mentions", "similarityScore": 0.80},
    {"id": "e28", "source": "co5", "target": "n2", "relationType": "usa", "similarityScore": 0.79},
    {"id": "e29", "source": "co2", "target": "per3", "relationType": "employs", "similarityScore": 0.95},
    {"id": "e30", "source": "co1", "target": "per2", "relationType": "employs", "similarityScore": 0.70},
    {"id": "e31", "source": "per1", "target": "n3", "relationType": "authored", "similarityScore": 0.72},
    {"id": "e32", "source": "per2", "target": "p3", "relationType": "invented", "similarityScore": 0.75},
    {"id": "e33", "source": "per3", "target": "n1", "relationType": "mentions", "similarityScore": 0.88},
]

MOCK_ECOSYSTEM = {
    "technologies": [
        {"name": "Generative AI (LLMs)", "category": "NLP/Generación", "maturity": 0.75, "adoption": 0.65, "trend": "rising", "keyPlayers": ["OpenAI", "Google DeepMind", "Meta AI"]},
        {"name": "Digital Twins / Simulación", "category": "Simulación", "maturity": 0.70, "adoption": 0.55, "trend": "rising", "keyPlayers": ["NVIDIA Omniverse", "Siemens", "Microsoft Azure"]},
        {"name": "Computer Vision (ViTs)", "category": "Visión Artificial", "maturity": 0.85, "adoption": 0.72, "trend": "stable", "keyPlayers": ["Meta AI", "Google", "OpenCV"]},
        {"name": "Edge AI / TinyML", "category": "Hardware IA", "maturity": 0.50, "adoption": 0.30, "trend": "emerging", "keyPlayers": ["Qualcomm", "ARM", "Syntiant"]},
    ],
    "relationships": [
        {"source": "Generative AI (LLMs)", "target": "Digital Twins / Simulación", "type": "complementa"},
        {"source": "Computer Vision (ViTs)", "target": "Edge AI / TinyML", "type": "se_ejecuta_en"},
        {"source": "Digital Twins / Simulación", "target": "Edge AI / TinyML", "type": "requiere"},
    ],
    "maturityLevels": {"emerging": {"count": 1, "avgMaturity": 0.50}, "rising": {"count": 2, "avgMaturity": 0.725}, "stable": {"count": 1, "avgMaturity": 0.85}, "declining": {"count": 0, "avgMaturity": 0.0}},
}
