"""GoogleFactCheckAdapter — spec 007 T051.

ExternalFactChecker adapter contra Google Fact Check Tools API.
Si VT_GOOGLE_FACTCHECK_API_KEY no esta configurado, degrada a
ClaimExternalValidation(status="not_found") sin error.
"""

from __future__ import annotations

import logging
from uuid import uuid4

import httpx

from vigilancia_multiagente.config.settings import get_settings
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

_FACTCHECK_URL = "https://factchecktools.googleapis.com/v1alpha1/claims:search"


class GoogleFactCheckAdapter:
    def __init__(
        self,
        errors_sink: list[StepError] | None = None,
    ) -> None:
        settings = get_settings()
        self._api_key = (
            settings.google_factcheck_api_key.get_secret_value()
            if settings.google_factcheck_api_key is not None
            else None
        )
        self._client = httpx.AsyncClient(timeout=15.0)
        self._errors = errors_sink

    async def close(self) -> None:
        await self._client.aclose()

    async def verify(self, claim: str) -> ClaimExternalValidation:
        if self._api_key is None:
            return ClaimExternalValidation(
                claim_id=uuid4(),
                external_db="google_factcheck",
                status=ExternalValidationStatus.NOT_FOUND,
            )
        params = {"query": claim, "key": self._api_key, "languageCode": "en"}
        try:
            response = await self._client.get(_FACTCHECK_URL, params=params)
            response.raise_for_status()
            data = response.json()
            claims = data.get("claims", [])
            if not claims:
                return ClaimExternalValidation(
                    claim_id=uuid4(),
                    external_db="google_factcheck",
                    status=ExternalValidationStatus.NOT_FOUND,
                )
            top = claims[0]
            text_rating = str(
                top.get("claimReview", [{}])[0].get("textualRating", "")
                if top.get("claimReview")
                else ""
            ).lower()
            if any(neg in text_rating for neg in ("false", "misleading", "incorrect", "pants-fire")):
                status = ExternalValidationStatus.CONTRADICTED
            elif any(pos in text_rating for pos in ("true", "correct", "accurate")):
                status = ExternalValidationStatus.VERIFIED
            else:
                status = ExternalValidationStatus.NOT_FOUND
            return ClaimExternalValidation(
                claim_id=uuid4(),
                external_db="google_factcheck",
                status=status,
                evidence_url=str(top.get("claimReview", [{}])[0].get("url", ""))
                if top.get("claimReview")
                else None,
            )
        except httpx.HTTPError as exc:
            logger.warning("GoogleFactCheck failed: %s", exc)
            self._record_error(exc, context={"claim_excerpt": claim[:100]})
            return ClaimExternalValidation(
                claim_id=uuid4(),
                external_db="google_factcheck",
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
                step_name="GoogleFactCheckAdapter.verify",
                reason=str(exc) or exc.__class__.__name__,
                exception_type=exc.__class__.__name__,
                context=dict(context) if context else {},
                severity=StepErrorSeverity.WARNING,
            )
        )
