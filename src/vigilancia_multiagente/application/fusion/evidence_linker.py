import contextlib

from vigilancia_multiagente.application.evaluation.source_scorer import SourceScorer
from vigilancia_multiagente.domain.models import BranchResult, BranchType, Finding, SourceRef

# Una fuente citada por >=2 ramas independientes es señal de consenso fuerte;
# se le da un pequeño boost de confianza por cada rama adicional.
_CONSENSUS_BOOST_PER_BRANCH = 0.05
_CONSENSUS_BOOST_CAP = 0.15


class EvidenceLinker:
    def __init__(
        self,
        source_scorer: SourceScorer | None = None,
        trust_repository: object | None = None,
    ) -> None:
        # Sin scorer inyectado => scorer vacío: ningún dominio tiene
        # reputación aprendida todavía, así que la confianza del agente no se
        # toca. Si se pasa trust_repository, refresh_learned_scores() recarga
        # el snapshot de source_trust antes de deduplicar.
        self._source_scorer = source_scorer or SourceScorer()
        self._trust_repository = trust_repository

    async def refresh_learned_scores(self) -> None:
        """Recarga el snapshot dominio→score desde source_trust.

        Las rutas la llaman antes de ``deduplicate_sources`` para que la
        reputación aprendida cross-session influya la confianza. No-op si no
        hay repositorio inyectado (tests / arranque sin BD).
        """
        repo = self._trust_repository
        if repo is None:
            return
        get_map = getattr(repo, "get_score_map", None)
        if get_map is None:
            return
        # El scoring aprendido es best-effort: si la BD falla, se sigue
        # con lo que el agente reportó (no se bloquea la fusión).
        with contextlib.suppress(Exception):
            self._source_scorer.learned_scores = await get_map()

    def deduplicate_sources(
        self, branch_results: list[BranchResult], use_scoring: bool = True
    ) -> list[SourceRef]:
        dedup: dict[str, SourceRef] = {}
        branches_by_url: dict[str, set[BranchType]] = {}
        for result in branch_results:
            for source in result.sources:
                normalized = _normalize_url(source.url)
                dedup.setdefault(normalized, source)
                branches_by_url.setdefault(normalized, set()).add(result.branch_type)

        sources = list(dedup.values())
        for source in sources:
            normalized = _normalize_url(source.url)
            if use_scoring:
                learned = self._source_scorer.score(source.url)
                # Sin reputación aprendida (dominio nuevo) NO se sobrescribe:
                # la nota inicial la pone el agente, no una tabla fija.
                if learned is not None:
                    source.confidence = min(source.confidence, learned)
            # Consenso cross-branch: fuentes corroboradas por varias ramas
            # independientes son más fiables que las de una sola.
            independent_branches = len(branches_by_url.get(normalized, ()))
            if independent_branches >= 2:
                boost = min(
                    _CONSENSUS_BOOST_CAP,
                    _CONSENSUS_BOOST_PER_BRANCH * (independent_branches - 1),
                )
                source.confidence = min(1.0, source.confidence + boost)
        return sources

    @staticmethod
    def consensus_by_url(branch_results: list[BranchResult]) -> dict[str, int]:
        """Nº de ramas independientes que citaron cada URL (señal de consenso)."""
        branches_by_url: dict[str, set[BranchType]] = {}
        for result in branch_results:
            for source in result.sources:
                branches_by_url.setdefault(_normalize_url(source.url), set()).add(
                    result.branch_type
                )
        return {url: len(branches) for url, branches in branches_by_url.items()}

    def link_findings(
        self, branch_results: list[BranchResult], dedup_sources: list[SourceRef]
    ) -> list[Finding]:
        canonical_by_url = {_normalize_url(source.url): source.id for source in dedup_sources}
        source_by_id = {source.id: source for result in branch_results for source in result.sources}
        available_ids = {source.id for source in dedup_sources}
        linked: list[Finding] = []
        for result in branch_results:
            for finding in result.findings:
                remapped_ids = []
                for source_id in finding.source_ids:
                    if source_id in available_ids:
                        remapped_ids.append(source_id)
                        continue
                    source = source_by_id.get(source_id)
                    if source is None:
                        continue
                    canonical_id = canonical_by_url.get(_normalize_url(source.url))
                    if canonical_id is not None:
                        remapped_ids.append(canonical_id)
                finding.source_ids = list(dict.fromkeys(remapped_ids))
                if finding.source_ids:
                    linked.append(finding)
        return linked


def _normalize_url(url: str) -> str:
    return url.strip().lower().rstrip("/")
