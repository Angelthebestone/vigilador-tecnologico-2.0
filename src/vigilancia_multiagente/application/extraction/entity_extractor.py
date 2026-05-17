"""
Extrae entidades nombradas (PERSON, COMPANY) con estrategia híbrida.

1. Metadata estructurada: si el payload trae campos de entidad (Exa
   category="people"/"company" devuelve nombre + empresa/afiliación como
   campos), se usan directamente. Esto puebla NamedEntity.affiliation, lo
   que habilita las aristas COMPANY-employs->PERSON en el grafo — relación
   que el NER de texto libre no puede inferir de forma fiable.
2. spaCy NER: para el texto libre (title/summary/statement) se usa un
   modelo estadístico entrenado (no listas hardcodeadas ni regex frágiles),
   cargado de forma perezosa y cacheado. Si el modelo no está instalado el
   NER degrada en silencio (la parte estructurada sigue funcionando).

Mapeo de etiquetas spaCy → dominio:
- PERSON / PER  → EntityType.PERSON
- ORG           → EntityType.COMPANY
"""

from __future__ import annotations

import logging
from functools import lru_cache
from uuid import UUID, uuid4

from vigilancia_multiagente.domain.models import BranchType, EntityType, NamedEntity

logger = logging.getLogger(__name__)

# Orden de preferencia de modelos. spaCy usa códigos ISO; los modelos _sm son
# ligeros (~15 MB) y suficientes para NER de PERSON/ORG.
_MODEL_PRIORITY: tuple[str, ...] = ("en_core_web_sm", "es_core_news_sm")

# Etiquetas NER que nos interesan, normalizadas a EntityType.
_LABEL_MAP: dict[str, EntityType] = {
    "PERSON": EntityType.PERSON,
    "PER": EntityType.PERSON,
    "ORG": EntityType.COMPANY,
}

# Confianza fija por tipo: spaCy no expone score por entidad en el pipeline
# estándar, así que asignamos un prior razonable según la etiqueta.
_CONFIDENCE: dict[EntityType, float] = {
    EntityType.PERSON: 0.75,
    EntityType.COMPANY: 0.80,
}

_MIN_ENTITY_LEN = 3


@lru_cache(maxsize=4)
def _load_nlp(model_name: str):
    """Carga y cachea un modelo spaCy. Devuelve None si no está disponible."""
    try:
        import spacy
    except ImportError:
        logger.warning("spaCy no está instalado; extracción de entidades deshabilitada.")
        return None
    try:
        return spacy.load(model_name, disable=["lemmatizer", "tagger", "parser"])
    except (OSError, IOError):
        logger.warning(
            "Modelo spaCy '%s' no encontrado. Ejecuta: python -m spacy download %s",
            model_name,
            model_name,
        )
        return None


def _get_pipeline():
    """Devuelve el primer modelo disponible según prioridad, o None."""
    for model_name in _MODEL_PRIORITY:
        nlp = _load_nlp(model_name)
        if nlp is not None:
            return nlp
    return None


def extract_entities(
    text: str,
    branch_type: BranchType,
    source_ids: list[UUID],
) -> list[NamedEntity]:
    """Extrae PERSON y COMPANY de texto libre vía spaCy NER.

    Deduplicada por nombre normalizado (lower). Si no hay modelo disponible o
    el texto está vacío, devuelve lista vacía sin lanzar excepción.
    """
    if not text or not text.strip():
        return []

    nlp = _get_pipeline()
    if nlp is None:
        return []

    try:
        doc = nlp(text)
    except Exception:  # noqa: BLE001 - NER no debe romper el pipeline de research
        logger.exception("Fallo procesando texto con spaCy NER")
        return []

    entities: dict[str, NamedEntity] = {}
    for ent in doc.ents:
        entity_type = _LABEL_MAP.get(ent.label_)
        if entity_type is None:
            continue
        name = ent.text.strip()
        if len(name) < _MIN_ENTITY_LEN:
            continue
        key = name.lower()
        if key in entities:
            continue
        entities[key] = NamedEntity(
            id=uuid4(),
            name=name,
            entity_type=entity_type,
            branch_type=branch_type,
            source_ids=list(source_ids),
            confidence=_CONFIDENCE[entity_type],
        )

    return list(entities.values())


# Nombres de campo plausibles para metadata estructurada de personas/empresas.
# Exa (category="people"/"company") y otros providers no comparten un esquema
# fijo; el execution_client devuelve el JSON crudo. Probamos varios alias.
_PERSON_NAME_FIELDS = ("author", "person", "fullName", "full_name", "personName")
_AFFILIATION_FIELDS = (
    "company",
    "affiliation",
    "organization",
    "employer",
    "currentCompany",
    "current_company",
)
_COMPANY_NAME_FIELDS = ("companyName", "company_name", "organization", "orgName")
# Indicios de que un payload representa una empresa (no una persona).
_COMPANY_HINT_FIELDS = ("headcount", "funding", "revenue", "domain", "website")


def _first_str(payload: dict, fields: tuple[str, ...]) -> str | None:
    for field in fields:
        value = payload.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _iter_records(payloads: list[dict]):
    """Aplana payloads y sus listas anidadas (results/items/data)."""
    for payload in payloads:
        if not isinstance(payload, dict):
            continue
        yield payload
        for container in ("results", "items", "data", "entities"):
            nested = payload.get(container)
            if isinstance(nested, list):
                for record in nested:
                    if isinstance(record, dict):
                        yield record


def _extract_structured(
    payloads: list[dict],
    branch_type: BranchType,
    source_ids: list[UUID],
) -> dict[str, NamedEntity]:
    """Extrae entidades de campos estructurados (Exa people/company, etc.).

    Si encuentra un nombre de persona junto a una afiliación, puebla
    NamedEntity.affiliation — esto habilita las aristas COMPANY-employs->PERSON
    en el grafo, que el NER de texto libre no puede inferir.
    """
    found: dict[str, NamedEntity] = {}
    for record in _iter_records(payloads):
        person_name = _first_str(record, _PERSON_NAME_FIELDS)
        affiliation = _first_str(record, _AFFILIATION_FIELDS)
        company_name = _first_str(record, _COMPANY_NAME_FIELDS)
        is_company_record = any(k in record for k in _COMPANY_HINT_FIELDS)

        if person_name and len(person_name) >= _MIN_ENTITY_LEN:
            key = person_name.lower()
            if key not in found:
                found[key] = NamedEntity(
                    id=uuid4(),
                    name=person_name,
                    entity_type=EntityType.PERSON,
                    branch_type=branch_type,
                    source_ids=list(source_ids),
                    affiliation=affiliation,
                    confidence=0.85 if affiliation else 0.78,
                )

        org_name = company_name or (affiliation if is_company_record else None)
        if org_name and len(org_name) >= _MIN_ENTITY_LEN:
            key = org_name.lower()
            if key not in found:
                found[key] = NamedEntity(
                    id=uuid4(),
                    name=org_name,
                    entity_type=EntityType.COMPANY,
                    branch_type=branch_type,
                    source_ids=list(source_ids),
                    confidence=0.85,
                )
    return found


def extract_from_payloads(
    payloads: list[dict],
    branch_type: BranchType,
    source_ids: list[UUID],
) -> list[NamedEntity]:
    """Extrae entidades combinando metadata estructurada + NER de texto libre.

    1. Campos estructurados (Exa people/company): nombre + afiliación directa.
    2. spaCy NER sobre title/summary/statement: cubre el resto del texto.
    Las entidades estructuradas tienen prioridad (conservan su affiliation).
    """
    entities: dict[str, NamedEntity] = _extract_structured(payloads, branch_type, source_ids)

    combined_parts: list[str] = []
    for payload in payloads:
        for key in ("title", "summary", "statement", "snippet", "abstract", "content"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                combined_parts.append(value)

    if combined_parts:
        text = "\n".join(combined_parts)
        for entity in extract_entities(text, branch_type, source_ids):
            entities.setdefault(entity.name.lower(), entity)

    return list(entities.values())
