"""Query expansion: una sola seed query limita el reclutamiento de fuentes.

Generar variaciones (reformulación técnica, bilingüe EN/ES, foco temporal)
amplía la cobertura: distintos buscadores indexan distinto y muchas fuentes
relevantes no usan exactamente las palabras de la query original.

Determinístico (sin LLM): transformaciones léxicas seguras. Si hay LLM
disponible se puede enchufar como generador de paráfrasis de mayor calidad.
"""

from __future__ import annotations

# Pares ES→EN de términos técnicos frecuentes en vigilancia tecnológica.
_BILINGUAL: dict[str, str] = {
    "inteligencia artificial": "artificial intelligence",
    "aprendizaje automático": "machine learning",
    "manufactura": "manufacturing",
    "industria": "industry",
    "mercado": "market",
    "patente": "patent",
    "riesgo": "risk",
    "tendencia": "trend",
    "investigación": "research",
    "tecnología": "technology",
}
_MAX_VARIANTS = 4


def expand_query(seed: str) -> list[str]:
    """Devuelve la query original + variaciones (sin duplicados, orden estable).

    La primera siempre es la original para no perder la intención literal.
    """
    seed = seed.strip()
    if not seed:
        return []

    variants: list[str] = [seed]
    lowered = seed.lower()

    # Variante bilingüe: traducir términos técnicos conocidos ES→EN.
    translated = lowered
    for es, en in _BILINGUAL.items():
        translated = translated.replace(es, en)
    if translated != lowered:
        variants.append(translated)

    # Variante técnica: pedir evidencia dura en vez del término genérico.
    variants.append(f"{seed} benchmark OR study OR technical evaluation")

    # Variante temporal: sesgar a lo más reciente (vigilancia = novedad).
    variants.append(f"{seed} latest 2024 2025 developments")

    # Dedup preservando orden, cap de seguridad.
    seen: set[str] = set()
    unique: list[str] = []
    for variant in variants:
        key = variant.lower()
        if key not in seen:
            seen.add(key)
            unique.append(variant)
    return unique[:_MAX_VARIANTS]
