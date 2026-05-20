"""Null Object implementations for optional OrchestratorService dependencies."""


class NullCrossSessionService:
    """No-op preloader — returns empty dict."""

    async def preload_session(self, query: str) -> dict:
        return {}


class NullTrendForecaster:
    """No-op forecaster — returns empty list."""

    async def analyze(self, session_data: dict) -> list:
        return []


class NullSourceScorer:
    """No-op source scorer — no-ops on all methods."""

    async def record_confirmation(self, source_a: str, source_b: str) -> dict:
        return {}

    async def record_contradiction(self, source_a: str, source_b: str) -> dict:
        return {}

    async def get_preferred_sources(self, limit: int = 5) -> list:
        return []


class NullReportGenerator:
    """No-op report generator — returns empty dict."""

    async def generate(self, findings: dict, report_type: str) -> dict:
        return {}
