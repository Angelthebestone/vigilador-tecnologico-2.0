"""WikidataFactCheckAdapter — spec 007 T052.

ExternalFactChecker adapter contra Wikidata SPARQL endpoint publico.
Sin clave necesaria: endpoint publico.
"""

from __future__ import annotations

import logging
from uuid import uuid4

import httpx

from vigilancia_multiagente.domain.evaluation_entities import (
    ClaimExternalValidation,
    ExternalValidationStatus,
)
from vigilancia_multiagente.domain.pipeline_errors import (
    StepError,
    StepErrorSeverity,
    Workstream,
)

logger = logging.getLogger(__name__)

_SPARQL_URL = "https://query.wikidata.org/sparql"


class WikidataFactCheckAdapter:
    def __init__(
        self,
        errors_sink: list[StepError] | None = None,
    ) -> None:
        self._client = httpx.AsyncClient(timeout=20.0)
        self._errors = errors_sink

    async def close(self) -> None:
        await self._client.aclose()

    async def verify(self, claim: str) -> ClaimExternalValidation:
        words = claim.split()[:6]
        query = " ".join(words)
        sparql = f"""
        SELECT ?item ?itemLabel ?desc WHERE {{
            ?item ?label "{query}"@en .
            OPTIONAL {{ ?item schema:description ?desc . }}
            SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        }} LIMIT 3
        """
        params = {"format": "json", "query": sparql}
        headers = {"User-Agent": "VigilanciaTecnologica/1.0"}
        try:
            response = await self._client.get(_SPARQL_URL, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()
            bindings = data.get("results", {}).get("bindings", [])
            if not bindings:
                return ClaimExternalValidation(
                    claim_id=uuid4(),
                    external_db="wikidata",
                    status=ExternalValidationStatus.NOT_FOUND,
                )
            return ClaimExternalValidation(
                claim_id=uuid4(),
                external_db="wikidata",
                status=ExternalValidationStatus.VERIFIED,
                evidence_url=str(bindings[0].get("item", {}).get("value", "")),
            )
        except httpx.HTTPError as exc:
            logger.warning("Wikidata SPARQL failed: %s", exc)
            self._record_error(exc, context={"claim_excerpt": claim[:100]})
            return ClaimExternalValidation(
                claim_id=uuid4(),
                external_db="wikidata",
                status=ExternalValidationStatus.NOT_FOUND,
            )

    def _record_error(
        self, exc: BaseException, *, context: dict[str, object] | None = None
    ) -> None:
        if self._errors is None:
            return
        self._errors.append(
            StepError(
                workstream=Workstream.WS_A,
                step_name="WikidataFactCheckAdapter.verify",
                reason=str(exc) or exc.__class__.__name__,
                exception_type=exc.__class__.__name__,
                context=dict(context) if context else {},
                severity=StepErrorSeverity.WARNING,
            )
        )
