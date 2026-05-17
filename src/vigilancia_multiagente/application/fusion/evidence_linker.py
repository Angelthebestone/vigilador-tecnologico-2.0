from vigilancia_multiagente.application.evaluation.source_scorer import SourceScorer
from vigilancia_multiagente.domain.models import BranchResult, Finding, SourceRef


class EvidenceLinker:
    def __init__(self) -> None:
        self._source_scorer = SourceScorer()

    def deduplicate_sources(
        self, branch_results: list[BranchResult], use_scoring: bool = True
    ) -> list[SourceRef]:
        dedup: dict[str, SourceRef] = {}
        for result in branch_results:
            for source in result.sources:
                normalized = _normalize_url(source.url)
                if normalized not in dedup:
                    dedup[normalized] = source
        sources = list(dedup.values())
        if use_scoring:
            for source in sources:
                source.confidence = min(
                    source.confidence,
                    self._source_scorer.score(source.url),
                )
        return sources

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
