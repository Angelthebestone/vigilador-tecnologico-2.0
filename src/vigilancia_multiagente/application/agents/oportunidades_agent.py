from vigilancia_multiagente.application.agents.base import BaseBranchAgent
from vigilancia_multiagente.application.governance.contract_loader import GovernanceContractLoader
from vigilancia_multiagente.application.governance.prompt_composer import PromptComposer
from vigilancia_multiagente.domain.models import BranchType
from vigilancia_multiagente.domain.system_base import SystemBase
from vigilancia_multiagente.infra.embeddings.gemini_gateway import GeminiEmbeddingGateway
from vigilancia_multiagente.infra.llm.minimax_client import MiniMaxClient
from vigilancia_multiagente.infra.mcp.execution_client import MCPExecutionClient
from vigilancia_multiagente.infra.mcp.provider_registry import MCPProviderRegistry


class OportunidadesAgent(BaseBranchAgent):
    def __init__(
        self,
        governance_loader: GovernanceContractLoader,
        provider_registry: MCPProviderRegistry,
        execution_client: MCPExecutionClient,
        embedding_gateway: GeminiEmbeddingGateway,
        minimax_client: MiniMaxClient | None = None,
        system_base: SystemBase | None = None,
        prompt_composer: PromptComposer | None = None,
    ) -> None:
        super().__init__(BranchType.OPORTUNIDADES, governance_loader, provider_registry, execution_client, embedding_gateway, minimax_client, system_base, prompt_composer)

