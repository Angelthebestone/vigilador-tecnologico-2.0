"""Post-research Q&A service. Answers follow-up questions from existing research state."""

import logging
from datetime import datetime
from uuid import UUID

from vigilancia_multiagente.domain.conversation_state import SessionContinuationState

logger = logging.getLogger(__name__)


class ConversationService:
    """
    Service that maintains session state after research completes
    and answers follow-up questions from the existing graph.
    """

    def __init__(self):
        self._active_sessions: dict[UUID, SessionContinuationState] = {}

    async def start_session(self, state: SessionContinuationState) -> None:
        """Register a continuation state for a completed research session."""
        self._active_sessions[state.session_id] = state

    def end_session(self, session_id: UUID) -> None:
        """Explicitly remove a conversation session."""
        self._active_sessions.pop(session_id, None)

    async def answer_from_graph(self, session_id: UUID, query: str) -> dict:
        """
        Answer a follow-up question from existing research graph and findings.

        Args:
            session_id: Active session ID
            query: Natural language question

        Returns:
            dict with:
              - answer: str (natural language response)
              - evidence: list of supporting findings
              - sources: list of source references
              - from_graph: bool (true if answered without new search)
        """
        state = self._active_sessions.get(session_id)
        if not state:
            return {"error": "Session not found or expired", "from_graph": False}

        state.last_active_at = datetime.utcnow()

        query_lower = query.lower()
        relevant = []
        for finding in state.findings_list:
            text = f"{finding.get('title', '')} {finding.get('content', '')} {finding.get('summary', '')}"
            if any(word in text.lower() for word in query_lower.split()):
                relevant.append(finding)

        graph_results = []
        if state.research_graph and isinstance(state.research_graph, dict):
            nodes = state.research_graph.get("nodes", [])
            for node in nodes:
                if any(word in str(node).lower() for word in query_lower.split()):
                    graph_results.append(node)

        if relevant or graph_results:
            return {
                "answer": f"Found {len(relevant)} relevant findings and {len(graph_results)} graph nodes related to your question.",
                "evidence": relevant[:5],
                "graph_nodes": graph_results[:5],
                "sources": list(set(f.get("source", "") for f in relevant[:5] if f.get("source"))),
                "from_graph": True,
            }

        return {
            "answer": None,
            "evidence": [],
            "sources": [],
            "from_graph": False,
        }

    async def needs_supplementary_search(self, session_id: UUID, query: str) -> dict:
        """
        Detect if a query cannot be answered from existing state.
        Returns a user-facing prompt asking for permission.

        Args:
            session_id: Active session ID
            query: The question that couldn't be answered from the graph

        Returns:
            dict with:
              - needs_search: bool
              - prompt: str (message to show user)
              - suggested_query: str (refined search query)
        """
        result = await self.answer_from_graph(session_id, query)

        if result.get("from_graph"):
            return {"needs_search": False, "answer": result}

        suggested = query.strip("?.").strip()
        if len(suggested) > 200:
            suggested = suggested[:200]

        return {
            "needs_search": True,
            "prompt": f'I couldn\'t find enough information in the current research to answer: "{query}"\n\nThis requires a new search. Should I launch one?',
            "suggested_query": suggested,
        }

    async def launch_supplementary_search(self, session_id: UUID, query: str) -> dict:
        """
        Launch a minimal supplementary search and merge results into existing state.

        Args:
            session_id: Active session
            query: Search query

        Returns:
            dict with new findings merged into existing state
        """
        state = self._active_sessions.get(session_id)
        if not state:
            return {"error": "Session not found"}

        state.supplementary_count += 1

        new_findings = await self._execute_minimal_search(query)

        state.findings_list.extend(new_findings)
        state.last_active_at = datetime.utcnow()

        return {
            "new_findings": new_findings,
            "total_findings": len(state.findings_list),
            "supplementary_count": state.supplementary_count,
        }

    async def _execute_minimal_search(self, query: str) -> list[dict]:
        """Execute a minimal search (stub - should call actual search infrastructure)."""
        logger.info("Supplementary search: %s", query)
        return []

    async def cleanup_expired_sessions(self, timeout_minutes: int = 30) -> int:
        """Remove sessions idle longer than timeout_minutes. Returns count removed."""
        now = datetime.utcnow()
        expired = [
            sid
            for sid, state in self._active_sessions.items()
            if (now - state.last_active_at).total_seconds() > timeout_minutes * 60
        ]
        for sid in expired:
            del self._active_sessions[sid]
        if expired:
            logger.info("Cleaned up %d expired conversation sessions", len(expired))
        return len(expired)
