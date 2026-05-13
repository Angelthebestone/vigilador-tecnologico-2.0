from vigilancia_multiagente.application.evaluation.source_scorer import SourceScorer
from vigilancia_multiagente.domain.models import BranchResult, Finding, SourceRef


class EvidenceLinker:
    def __init__(self) -> None:
        self._source_scorer = SourceScorer()

    def deduplicate_sources(self, branch_results: list[BranchResult], use_scoring: bool = True) -> list[SourceRef]:
        dedup: dict[str, SourceRef] = {}
        for result in branch_results:
            for source in result.sources:
                normalized = source.url.strip().lower()
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

    def link_findings(self, branch_results: list[BranchResult], dedup_sources: list[SourceRef]) -> list[Finding]:
        available_ids = {source.id for source in dedup_sources}
        linked: list[Finding] = []
        for result in branch_results:
            for finding in result.findings:
                finding.source_ids = [source_id for source_id in finding.source_ids if source_id in available_ids]
                if finding.source_ids:
                    linked.append(finding)
        return linked

