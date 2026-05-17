from uuid import UUID, uuid4

from vigilancia_multiagente.config.settings import get_settings
from vigilancia_multiagente.domain.models import BranchConfig, BranchType, ResearchPlan
from vigilancia_multiagente.domain.system_base import MiniMaxMessage
from vigilancia_multiagente.infra.llm.minimax_client import MiniMaxClient
from vigilancia_multiagente.infra.prompts.loader import load_prompt

DEFAULT_PROVIDERS: dict[BranchType, list[str]] = {
    BranchType.AVANCES: ["tavily", "exa", "jina"],
    BranchType.COMERCIAL: ["exa", "brave", "tavily"],
    BranchType.RIESGO: ["brave", "firecrawl", "jina"],
    BranchType.PI_NORMATIVA: ["google_scholar", "arxiv", "jina"],
    BranchType.COMPETITIVO: ["exa", "brave", "jina"],
    BranchType.OPORTUNIDADES: ["tavily", "exa", "brave"],
}


class PlanBuilder:
    """Builds research plans.

    The planner emits only investigation scope, branch goals, and priorities.
    Global agent rules are sourced from the canonical system base (system-base.md).
    """

    async def build(
        self,
        session_id: UUID,
        answers: dict[str, str],
        user_query: str = "",
        llm: MiniMaxClient | None = None,
        preload_context: dict | None = None,
    ) -> ResearchPlan:
        settings = get_settings()
        horizon = answers.get("scope-horizon", "mid-term")
        geo = answers.get("scope-geo", "global")
        recurring = (preload_context or {}).get("recurring_entities") or []
        # Las 2-3 entidades ya investigadas en sesiones previas se vuelven foco
        # "delta": en vez de re-investigarlas, se busca lo nuevo sobre ellas.
        delta_focus = [str(term) for term in recurring[:3] if str(term).strip()]

        if llm is not None and user_query:
            import json

            try:
                prompt = load_prompt("orchestration/planning").format(
                    user_query=user_query, clarification_answers=json.dumps(answers)
                )
                response = await llm.complete(
                    messages=[MiniMaxMessage(role="user", content=prompt)]
                )
                data = json.loads(response.content)
                branches_data = data.get("branches", [])
                branches = _parse_branches_from_llm(branches_data)
                if branches:
                    _inject_delta_focus(branches, delta_focus)
                    return ResearchPlan(
                        id=uuid4(),
                        session_id=session_id,
                        version=1,
                        system_base_version=settings.system_base_version,
                        branches=branches,
                        global_constraints={
                            "depth_limit": 3,
                            "geographic_scope": geo,
                            "temporal_policy": "dynamic",
                        },
                        requires_approval=True,
                    )
            except (json.JSONDecodeError, KeyError, TypeError, RuntimeError):
                pass

        branches = [
            BranchConfig(
                branch_type=branch_type,
                focus_queries=[
                    f"{branch_type.value.lower()} technology signals {horizon}",
                    f"{branch_type.value.lower()} market context {geo}",
                    *_delta_queries(branch_type, delta_focus),
                ],
                mcp_providers=DEFAULT_PROVIDERS[branch_type],
            )
            for branch_type in BranchType
        ]
        return ResearchPlan(
            id=uuid4(),
            session_id=session_id,
            version=1,
            system_base_version=settings.system_base_version,
            branches=branches,
            global_constraints={
                "depth_limit": 3,
                "geographic_scope": geo,
                "temporal_policy": "dynamic",
            },
            requires_approval=True,
        )


def _delta_queries(branch_type: BranchType, delta_focus: list[str]) -> list[str]:
    """Queries 'delta' para re-investigar lo nuevo sobre entidades ya conocidas."""
    return [
        f"new developments on {term} since prior research ({branch_type.value.lower()})"
        for term in delta_focus
    ]


def _inject_delta_focus(branches: list[BranchConfig], delta_focus: list[str]) -> None:
    if not delta_focus:
        return
    for branch in branches:
        branch.focus_queries.extend(_delta_queries(branch.branch_type, delta_focus))


def _parse_branches_from_llm(data: list[dict]) -> list[BranchConfig]:
    """Parse LLM JSON output into BranchConfig list with fallback on parse failure per branch."""
    branches: list[BranchConfig] = []
    for item in data:
        try:
            bt = BranchType(item.get("type", "").upper())
        except ValueError:
            continue
        providers = [
            provider
            for provider in item.get("mcp_providers", DEFAULT_PROVIDERS[bt])
            if provider != "serper"
        ] or DEFAULT_PROVIDERS[bt]
        branches.append(
            BranchConfig(
                branch_type=bt,
                focus_queries=list(item.get("focus_queries", [])),
                mcp_providers=providers,
                priority_weight=item.get("priority_weight"),
            )
        )
    return branches
