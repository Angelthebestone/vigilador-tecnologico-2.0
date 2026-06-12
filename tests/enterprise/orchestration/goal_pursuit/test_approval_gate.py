"""Tests for ApprovalGate: blocks without approval, unblocks with, token expiry."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from vigilancia_multiagente.enterprise.orchestration.goal_pursuit.approval_gate import (
    ApprovalGate,
    ApprovalRequestPort,
)
from vigilancia_multiagente.enterprise.orchestration.goal_pursuit.capability_token import (
    CapabilityToken,
)


class FakeApprovalPort(ApprovalRequestPort):
    """Fake approval port with configurable approval status."""

    def __init__(self, approved: bool = False) -> None:
        self._approved = approved
        self.requests: list[tuple[str, str]] = []

    def submit_request(self, goal_id: object, context: str) -> str:
        req_id = f"req-{len(self.requests)}"
        self.requests.append((str(goal_id), context))
        return req_id

    def is_approved(self, request_id: str) -> bool:
        return self._approved


def _valid_token() -> CapabilityToken:
    return CapabilityToken.issue(uuid4(), ttl_seconds=3600, scopes=frozenset({"all"}))


def _expired_token() -> CapabilityToken:
    past = datetime.now(tz=UTC) - timedelta(seconds=100)
    return CapabilityToken(
        goal_id=uuid4(),
        ttl_seconds=10,
        scopes=frozenset({"all"}),
        issued_at=past,
        expires_at=past + timedelta(seconds=10),
        token_id=uuid4(),
    )


def test_gate_blocks_without_approval() -> None:
    port = FakeApprovalPort(approved=False)
    gate = ApprovalGate(port)
    result = gate.request_approval(uuid4(), "critical action", _valid_token())
    assert result.approved is False
    assert result.reason == "awaiting_approval"


def test_gate_unblocks_with_approval() -> None:
    port = FakeApprovalPort(approved=True)
    gate = ApprovalGate(port)
    result = gate.request_approval(uuid4(), "critical action", _valid_token())
    assert result.approved is True
    assert result.reason == "human_approved"


def test_expired_token_maintains_pause() -> None:
    port = FakeApprovalPort(approved=True)
    gate = ApprovalGate(port)
    result = gate.request_approval(uuid4(), "action", _expired_token())
    assert result.approved is False
    assert "expired" in result.reason
