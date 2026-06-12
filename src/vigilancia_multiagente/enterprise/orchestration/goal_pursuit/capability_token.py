# ROADMAP F5b - fuera de MVP 021; no registrar en runtime
"""Capability token: time-bounded authorization for autonomous goal execution."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass(frozen=True, slots=True)
class CapabilityToken:
    """Immutable authorization token with TTL and scopes for a goal."""

    goal_id: UUID
    ttl_seconds: int
    scopes: frozenset[str]
    issued_at: datetime
    expires_at: datetime
    token_id: UUID

    @classmethod
    def issue(
        cls,
        goal_id: UUID,
        ttl_seconds: int | None = None,
        scopes: frozenset[str] = frozenset(),
    ) -> CapabilityToken:
        """Issue a new capability token with the given TTL."""
        if ttl_seconds is None:
            from vigilancia_multiagente.config.settings import get_settings

            ttl_seconds = get_settings().goal_pursuit_token_ttl_sec
        now = datetime.now(tz=UTC)
        from datetime import timedelta

        expires = now + timedelta(seconds=ttl_seconds)
        return cls(
            goal_id=goal_id,
            ttl_seconds=ttl_seconds,
            scopes=scopes,
            issued_at=now,
            expires_at=expires,
            token_id=uuid4(),
        )

    def is_expired(self) -> bool:
        """Return True if the token has expired."""
        return datetime.now(tz=UTC) >= self.expires_at

    def remaining_seconds(self) -> float:
        """Return remaining seconds before expiration (0 if already expired)."""
        delta = (self.expires_at - datetime.now(tz=UTC)).total_seconds()
        return max(0.0, delta)

    def reissue(self, new_ttl: int) -> CapabilityToken:
        """Reissue a new token with extended TTL, preserving goal_id and scopes."""
        return CapabilityToken.issue(
            goal_id=self.goal_id,
            ttl_seconds=new_ttl,
            scopes=self.scopes,
        )

    def to_dict(self) -> dict[str, object]:
        """Serialize to dict for JSONB persistence."""
        return {
            "token_id": str(self.token_id),
            "goal_id": str(self.goal_id),
            "ttl_seconds": self.ttl_seconds,
            "scopes": sorted(self.scopes),
            "issued_at": self.issued_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
        }
