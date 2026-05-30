"""ApprovalGate: pauses goal execution at critical points until human approval."""

from __future__ import annotations

from uuid import UUID

from vigilancia_multiagente.enterprise.orchestration.goal_pursuit.capability_token import (
    CapabilityToken,
)


class ApprovalRequestPort:
    """Port for submitting approval requests and checking status."""

    def submit_request(self, goal_id: UUID, context: str) -> str:
        """Submit approval request. Returns request_id."""
        raise NotImplementedError

    def is_approved(self, request_id: str) -> bool:
        """Check if the request has been approved."""
        raise NotImplementedError


class ApprovalGate:
    """Blocks goal execution at critical points pending human approval.

    Integrates with capability token: if token expires during wait, stays paused.
    """

    def __init__(self, approval_port: ApprovalRequestPort) -> None:
        self._port = approval_port

    def request_approval(
        self, goal_id: UUID, context: str, token: CapabilityToken
    ) -> ApprovalResult:
        """Request approval. Returns result indicating if approved or blocked."""
        if token.is_expired():
            return ApprovalResult(
                approved=False,
                reason="capability_token_expired",
                request_id=None,
            )

        request_id = self._port.submit_request(goal_id, context)
        approved = self._port.is_approved(request_id)

        if approved:
            return ApprovalResult(
                approved=True, reason="human_approved", request_id=request_id
            )

        # Check token again after waiting
        if token.is_expired():
            return ApprovalResult(
                approved=False,
                reason="capability_token_expired_during_wait",
                request_id=request_id,
            )

        return ApprovalResult(
            approved=False, reason="awaiting_approval", request_id=request_id
        )


class ApprovalResult:
    """Result of an approval gate check."""

    __slots__ = ("approved", "reason", "request_id")

    def __init__(self, approved: bool, reason: str, request_id: str | None) -> None:
        self.approved = approved
        self.reason = reason
        self.request_id = request_id
