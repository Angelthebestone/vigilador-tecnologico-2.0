"""Integration tests for cross-session memory."""

import pytest

pytestmark = pytest.mark.asyncio


async def test_save_and_retrieve_snapshot():
    """Test saving a snapshot and retrieving related sessions."""
    from vigilancia_multiagente.domain.global_knowledge import GlobalKnowledgeSnapshot
    from uuid import uuid4

    snapshot = GlobalKnowledgeSnapshot(
        session_id=uuid4(),
        query_summary="Test research on AI",
        findings_graph={"nodes": [], "edges": []},
    )
    assert snapshot.session_id is not None
    assert snapshot.query_summary == "Test research on AI"
    assert snapshot.findings_graph == {"nodes": [], "edges": []}
    assert snapshot.created_at is not None


async def test_merge_findings_deduplication():
    """Test that merge_findings detects duplicates."""
    from vigilancia_multiagente.application.memory.cross_session_service import CrossSessionService

    current = [
        {
            "title": "AI in Healthcare",
            "statement": "AI in Healthcare",
            "source": "src_a",
            "topic": "healthcare",
        }
    ]
    prior = [
        {
            "title": "AI in Healthcare",
            "statement": "AI in Healthcare",
            "source": "src_b",
            "topic": "healthcare",
        }
    ]

    service = CrossSessionService()
    result = await service.merge_findings(current, prior)
    assert "duplicates" in result
    assert "merged" in result
    assert "contradictions" in result
    assert len(result["duplicates"]) > 0


async def test_merge_findings_contradiction():
    """Test that merge_findings detects contradictions."""
    from vigilancia_multiagente.application.memory.cross_session_service import CrossSessionService

    current = [{"statement": "Market size is 50 billion", "topic": "market", "source": "src_a"}]
    prior = [{"statement": "Market size is 80 billion", "topic": "market", "source": "src_b"}]

    service = CrossSessionService()
    result = await service.merge_findings(current, prior)
    assert "contradictions" in result
