from enum import StrEnum


class SessionStatus(StrEnum):
    DRAFT = "DRAFT"
    CLARIFYING = "CLARIFYING"
    PLANNING = "PLANNING"
    APPROVED = "APPROVED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELED = "CANCELED"


VALID_TRANSITIONS: dict[SessionStatus, set[SessionStatus]] = {
    SessionStatus.DRAFT: {SessionStatus.CLARIFYING, SessionStatus.CANCELED},
    SessionStatus.CLARIFYING: {SessionStatus.PLANNING, SessionStatus.CANCELED},
    SessionStatus.PLANNING: {SessionStatus.APPROVED, SessionStatus.CANCELED},
    SessionStatus.APPROVED: {SessionStatus.EXECUTING, SessionStatus.CANCELED},
    SessionStatus.EXECUTING: {
        SessionStatus.COMPLETED,
        SessionStatus.FAILED,
        SessionStatus.CANCELED,
    },
    SessionStatus.COMPLETED: set(),
    SessionStatus.FAILED: set(),
    SessionStatus.CANCELED: set(),
}


def ensure_transition(current: SessionStatus, target: SessionStatus) -> None:
    if target not in VALID_TRANSITIONS[current]:
        raise ValueError(f"Invalid session transition: {current} -> {target}")

