from vigilancia_multiagente.application.agents.base import BaseBranchAgent
from vigilancia_multiagente.domain.models import BranchType
from vigilancia_multiagente.domain.ports.provider_registry import ProviderRegistry


class AvancesAgent(BaseBranchAgent):
    def __init__(
        self,
        governance_loader,
        provider_registry: ProviderRegistry,
        execution_client,
        embedding_gateway,
        minimax_client,
        system_base,
        prompt_composer,
        **kwargs,
    ):
        super().__init__(
            branch_type=BranchType.AVANCES,
            governance_loader=governance_loader,
            provider_registry=provider_registry,
            execution_client=execution_client,
            embedding_gateway=embedding_gateway,
            minimax_client=minimax_client,
            system_base=system_base,
            prompt_composer=prompt_composer,
            **kwargs,
        )
