"""Tests for CapabilityToken: emission, expiration, remaining, reissue."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from vigilancia_multiagente.enterprise.orchestration.goal_pursuit.capability_token import (
    CapabilityToken,
)


def test_issue_with_correct_ttl() -> None:
    goal_id = uuid4()
    token = CapabilityToken.issue(goal_id, ttl_seconds=3600, scopes=frozenset({"read"}))
    assert token.goal_id == goal_id
    assert token.ttl_seconds == 3600
    assert token.scopes == frozenset({"read"})
    assert token.expires_at > token.issued_at
    expected_delta = timedelta(seconds=3600)
    actual_delta = token.expires_at - token.issued_at
    assert abs(actual_delta.total_seconds() - expected_delta.total_seconds()) < 2


def test_is_expired_returns_true_after_ttl() -> None:
    goal_id = uuid4()
    past = datetime.now(tz=timezone.utc) - timedelta(seconds=100)
    token = CapabilityToken(
        goal_id=goal_id,
        ttl_seconds=10,
        scopes=frozenset({"write"}),
        issued_at=past,
        expires_at=past + timedelta(seconds=10),
        token_id=uuid4(),
    )
    assert token.is_expired() is True


def test_remaining_seconds_calculates_correctly() -> None:
    goal_id = uuid4()
    token = CapabilityToken.issue(goal_id, ttl_seconds=7200, scopes=frozenset({"all"}))
    remaining = token.remaining_seconds()
    assert 7198 < remaining <= 7200


def test_reissue_generates_new_token_with_extended_ttl() -> None:
    goal_id = uuid4()
    original = CapabilityToken.issue(goal_id, ttl_seconds=100, scopes=frozenset({"a", "b"}))
    reissued = original.reissue(new_ttl=5000)
    assert reissued.goal_id == goal_id
    assert reissued.ttl_seconds == 5000
    assert reissued.scopes == frozenset({"a", "b"})
    assert reissued.token_id != original.token_id
    assert reissued.expires_at > original.expires_at
