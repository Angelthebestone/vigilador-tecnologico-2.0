from pathlib import Path
from datetime import UTC, datetime
from uuid import uuid4

from vigilancia_multiagente.application.graph.knowledge_graph_service import KnowledgeGraphService
from vigilancia_multiagente.domain.models import BranchType, Finding, SourceRef


def test_knowledge_graph_service_builds_traceable_graph():
    service = KnowledgeGraphService()
    session_id = uuid4()
    source = SourceRef(
        id=uuid4(),
        session_id=session_id,
        url="https://example.com/a",
        provider="tavily",
        branch_type=BranchType.COMERCIAL,
        accessed_at=datetime.now(UTC),
        title="Source A",
    )
    finding = Finding(
        id=uuid4(),
        topic="Commercial signal",
        statement="Signal found",
        confidence=0.8,
        source_ids=[source.id],
    )

    graph = service.build(session_id, [finding], [source])

    assert graph.session_id == session_id
    assert graph.nodes[0]["type"] == "SOURCE"
    assert graph.edges[0]["relation_type"] == "REFERENCES"
    assert service.sources_for_node(graph.nodes[1]["id"], graph) == [graph.nodes[0]["id"]]


def test_contract_files_match_backend_expectations():
    api_contract = Path("specs/002-vigilancia-multiagente/contracts/research-api.yaml").read_text(encoding="utf-8")
    governance_contract = Path("specs/002-vigilancia-multiagente/contracts/agent-governance.md").read_text(encoding="utf-8")
    mcp_manifest = Path("specs/002-vigilancia-multiagente/contracts/mcp-providers.json").read_text(encoding="utf-8")
    compose_file = Path("docker-compose.yml").read_text(encoding="utf-8")

    assert "/api/v2" in api_contract
    assert "/research/{session_id}/graph" in api_contract
    assert "Matriz agente→skill MCP" in governance_contract
    assert '"providers"' in mcp_manifest
    assert "services:" in compose_file
    assert "VT_EMBEDDING_API_KEY" in compose_file

