"""Mock data for branch iterations, replan signals, and cross-session helpers."""

CROSS_SESSION_RECURRING = ["Toyota", "gemelos digitales"]


def _delta_focus(branch: str) -> list[str]:
    return [
        f"new developments on {term} since prior research ({branch.lower()})"
        for term in CROSS_SESSION_RECURRING
    ]


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
            "reasoning": "Cuantificando la evolución bibliométrica del campo con datos estructurados de OpenAlex.",
            "toolCall": {
                "tool": "analyze_topic_trends",
                "query": "generative AI automotive manufacturing 2018-2024",
                "result": "Crecimiento de publicaciones del 41% anual; pico de citas en 2023.",
            },
            "result": "OpenAlex confirma tendencia exponencial: 1.847 trabajos en 2024 vs 312 en 2019.",
            "confidence": 0.89,
        },
        {
            "stepNumber": 5,
            "reasoning": "Ejecutando análisis estadístico vía sandbox.",
            "toolCall": {
                "tool": "execute_code",
                "query": "Analizar correlación año vs citas y proyectar tendencia con scipy",
                "code": "import numpy as np\nfrom scipy import stats\nanios = np.array([2018, 2019, 2020, 2021, 2022, 2023, 2024])\npublicaciones = np.array([210, 312, 498, 760, 1180, 1530, 1847])\nslope, intercept, r, p, se = stats.linregress(anios, publicaciones)\nfuturos = np.array([2025, 2026, 2027])\nproyeccion = slope * futuros + intercept\nprint(f'slope={slope:.2f} r={r:.3f} p={p:.4f}')\nprint('proyeccion:', proyeccion.round().astype(int).tolist())",
                "stdout": "slope=283.93 r=0.987 p=0.0002\nproyeccion: [2456, 3098, 3740]",
                "result": "Coeficiente de correlación: 0.87 (p<0.01). Proyección: 2.450 publicaciones en 2025, 3.100 en 2026.",
            },
            "result": "Análisis numérico vía sandbox confirma correlación significativa.",
            "confidence": 0.94,
        },
        {
            "stepNumber": 6,
            "reasoning": "Generando visualización publicable de la proyección de tendencia.",
            "toolCall": {
                "tool": "visualize",
                "query": "Publicaciones IA manufactura 2018-2027",
                "code": "import matplotlib.pyplot as plt\nplt.rcParams.update({'axes.spines.top': False, 'axes.spines.right': False, 'axes.grid': True, 'grid.alpha': 0.25})\nfig, ax = plt.subplots(figsize=(7, 4))\nanios_hist = [2018, 2019, 2020, 2021, 2022, 2023, 2024]\npub_hist = [210, 312, 498, 760, 1180, 1530, 1847]\nanios_proy = [2024, 2025, 2026, 2027]\npub_proy = [1847, 2456, 3098, 3740]\nax.plot(anios_hist, pub_hist, 'o-', color='#34531f', label='Histórico')\nax.plot(anios_proy, pub_proy, 's--', color='#9aab1f', label='Proyección')\nax.set_title('Publicaciones IA en manufactura')\nax.set_xlabel('Año'); ax.set_ylabel('Publicaciones')\nax.legend()\nfig.savefig('trend.png', dpi=130, bbox_inches='tight')",
                "stdout": "Figura guardada: trend.png",
                "image": "/charts/trend-bibliometric.png",
                "result": "Gráfico de proyección generado.",
            },
            "result": "Gráfico de proyección generado: muestra el crecimiento histórico y proyección hasta 2027.",
            "confidence": 0.92,
        },
    ],
    "COMERCIAL": [
        {
            "stepNumber": 1,
            "reasoning": "Mapeando el tamaño y tasa de crecimiento del mercado global de IA en manufactura automotriz.",
            "toolCall": {"tool": "tavily_search", "query": "AI automotive manufacturing market size CAGR 2024 2030", "result": "Múltiples reportes de analistas con proyecciones de mercado."},
            "result": "Mercado valorado en $4.2B en 2024, con CAGR del 28.3% hacia 2030 (proyección: $18.7B).",
            "confidence": 0.85,
        },
        {
            "stepNumber": 2,
            "reasoning": "Analizando rondas de inversión y M&A en startups de IA.",
            "toolCall": {"tool": "exa_search", "query": "AI automotive manufacturing startup funding rounds 2023 2024", "result": "47 transacciones de M&A e inversión identificadas."},
            "result": "Inversión récord de $2.1B en H1 2024, liderada por Mobileye, Cognex y Scale AI.",
            "confidence": 0.79,
        },
    ],
    "RIESGO": [
        {
            "stepNumber": 1,
            "reasoning": "Identificando vectores de riesgo cibernético en sistemas IA conectados.",
            "toolCall": {"tool": "tavily_search", "query": "cybersecurity AI systems automotive factory OT security 2024", "result": "Reportes de incidentes y análisis de vulnerabilidades."},
            "result": "El 67% de fabricantes automotrices reportó intentos de intrusión en sistemas OT conectados a IA en 2023.",
            "confidence": 0.87,
        },
        {
            "stepNumber": 2,
            "reasoning": "Revisando casos de fallos de IA que derivaron en recalls.",
            "toolCall": {"tool": "brave_search", "query": "AI failure automotive production line halt recall incident 2023 2024", "result": "6 incidentes documentados."},
            "result": "Identificados 6 incidentes donde fallos de modelos IA provocaron paros de línea >4 horas, con pérdidas de $3.2M.",
            "confidence": 0.83,
        },
    ],
    "PI_NORMATIVA": [
        {
            "stepNumber": 1,
            "reasoning": "Analizando la evolución de patentes en IA aplicada a manufactura automotriz.",
            "toolCall": {"tool": "google_scholar", "query": "patents generative AI automotive manufacturing USPTO EPO 2023 2024", "result": "340 registros relevantes."},
            "result": "Toyota lidera con 89 patentes activas; seguida de Bosch (72) y Volkswagen (61).",
            "confidence": 0.90,
        },
        {
            "stepNumber": 2,
            "reasoning": "Revisando el marco regulatorio emergente para IA.",
            "toolCall": {"tool": "fetch", "query": "EU AI Act automotive manufacturing compliance requirements 2024", "result": "Documentos oficiales de la Comisión Europea."},
            "result": "El EU AI Act clasifica los sistemas IA de control de producción como 'Alto Riesgo', requiriendo auditorías obligatorias desde 2026.",
            "confidence": 0.93,
        },
        {
            "stepNumber": 3,
            "reasoning": "Localizando papers fundacionales vía OpenAlex.",
            "toolCall": {"tool": "find_seminal_papers", "query": "AI manufacturing process control foundational", "result": "7 papers fundacionales con >500 citas."},
            "result": "Identificados 7 trabajos fundacionales que actúan como prior art clave.",
            "confidence": 0.91,
        },
        {
            "stepNumber": 4,
            "reasoning": "Descargando el paper fundacional más citado.",
            "toolCall": {"tool": "download_paper", "query": "arxiv:2103.xxxxx foundational AI manufacturing", "result": "Paper descargado."},
            "result": "Paper fundacional descargado.",
            "confidence": 0.88,
        },
        {
            "stepNumber": 5,
            "reasoning": "Extrayendo el texto del paper descargado.",
            "toolCall": {"tool": "read_paper", "query": "arxiv:2103.xxxxx full text", "result": "Texto markdown del paper extraído."},
            "result": "Reivindicaciones técnicas del paper analizadas.",
            "confidence": 0.92,
        },
    ],
    "COMPETITIVO": [
        {
            "stepNumber": 1,
            "reasoning": "Mapeando las estrategias de los principales OEM.",
            "toolCall": {"tool": "tavily_search", "query": "Toyota BMW Volkswagen Mercedes generative AI manufacturing strategy 2024", "result": "Reportes anuales de los 5 principales OEM."},
            "result": "Toyota lidera con 'Toyota Production System AI' ($800M); BMW con iFACTORY; Volkswagen con CARIAD.",
            "confidence": 0.86,
        },
        {
            "stepNumber": 2,
            "reasoning": "Analizando la ventaja competitiva de Tesla.",
            "toolCall": {"tool": "exa_search", "query": "Tesla Gigafactory AI automation Dojo manufacturing advantage 2024", "result": "Análisis técnicos y comparativas."},
            "result": "Tesla produce 1 vehículo cada 40s con 65% menos personal de QC gracias a visión IA.",
            "confidence": 0.88,
        },
        {
            "stepNumber": 3,
            "reasoning": "Mapeando líderes técnicos de IA en manufactura vía OpenAlex.",
            "toolCall": {"tool": "search_authors_by_expertise", "query": "AI manufacturing automotive process optimization experts", "result": "Top 15 investigadores por h-index."},
            "result": "3 de los 5 investigadores líderes están afiliados a Toyota Research y Bosch.",
            "confidence": 0.84,
        },
    ],
    "OPORTUNIDADES": [
        {
            "stepNumber": 1,
            "reasoning": "Identificando nichos de mercado desatendidos.",
            "toolCall": {"tool": "tavily_search", "query": "AI automotive manufacturing opportunity niche underserved market 2024", "result": "Análisis de gaps tecnológicos."},
            "result": "El 78% de proveedores Tier-2/3 aún no han adoptado IA en QC; oportunidad de $6.8B para 2027.",
            "confidence": 0.81,
        },
        {
            "stepNumber": 2,
            "reasoning": "Explorando oportunidades de colaboración universidad-OEM en LatAm.",
            "toolCall": {"tool": "brave_search", "query": "Mexico India emerging market AI automotive manufacturing opportunity", "result": "Estudios de factibilidad y programas gubernamentales."},
            "result": "México e India emergen como hubs de manufactura inteligente: $1.2B en incentivos gubernamentales.",
            "confidence": 0.77,
        },
        {
            "stepNumber": 3,
            "reasoning": "Cuantificando el tamaño de oportunidad por segmento con pandas.",
            "toolCall": {
                "tool": "execute_code",
                "query": "Analizar distribución de oportunidad $6.8B por segmento y región",
                "code": "import pandas as pd\ndf = pd.DataFrame({'segmento': ['Tier-1', 'Tier-2', 'Tier-2', 'Tier-3', 'Tier-3'], 'region': ['Global', 'APAC', 'LatAm', 'LatAm', 'África'], 'oportunidad_bn': [1.22, 2.59, 1.08, 1.36, 0.55]})\ntotal = df['oportunidad_bn'].sum()\npor_segmento = df.groupby('segmento')['oportunidad_bn'].sum() / total\nprint('total:', round(total, 2))\nprint((por_segmento * 100).round(0).to_dict())",
                "stdout": "total: 6.8\n{'Tier-1': 18.0, 'Tier-2': 54.0, 'Tier-3': 28.0}",
                "result": "Segmento Tier-2 concentra 54% de la oportunidad.",
            },
            "result": "Análisis cuantitativo completado: la oportunidad de $6.8B se distribuye 54% en Tier-2.",
            "confidence": 0.84,
        },
        {
            "stepNumber": 4,
            "reasoning": "Ejecutando clustering sobre datos de oportunidad.",
            "toolCall": {
                "tool": "execute_code",
                "query": "Clustering de regiones por oportunidad",
                "code": "from sklearn.cluster import KMeans\nimport numpy as np\nX = np.array([[1.22, 0.4], [2.59, 0.8], [1.08, 0.6], [1.36, 0.7], [0.55, 0.3]])\nkm = KMeans(n_clusters=2, random_state=42, n_init='auto')\nlabels = km.fit_predict(X)\nprint('clusters:', labels.tolist())",
                "stdout": "clusters: [0, 1, 0, 0, 0]",
                "result": "Segmentación clara: APAC como outlier de alto valor.",
            },
            "result": "Clustering identifica que APAC concentra > 38% del valor total de oportunidad.",
            "confidence": 0.80,
        },
    ],
}
