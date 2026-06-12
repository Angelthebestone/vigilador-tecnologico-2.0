"""AgentModifier: single entry point for agent modifications to config files.

Orchestrates: diff generation, approval gate, DB persistence, JSONL persistence,
atomic file write, superseded chain, and rollback. Order: DB → JSONL → file,
with compensation on failure.
"""

from __future__ import annotations

import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from vigilancia_multiagente.enterprise.governance.approval_gate import (
    ModeAuditSettings,
    requires_approval,
)
from vigilancia_multiagente.enterprise.governance.audit_persistence import AuditPersistence
from vigilancia_multiagente.enterprise.governance.diff_engine import (
    LLMClient,
    compute_diff,
    generate_summary,
)
from vigilancia_multiagente.enterprise.governance.metrics import (
    agent_modifications_pending_approval,
    agent_modifications_reverted_total,
    agent_modifications_total,
)
from vigilancia_multiagente.enterprise.governance.models import (
    ModificationRecord,
    ModificationResult,
    ModificationStatus,
    RollbackResult,
)
from vigilancia_multiagente.enterprise.governance.superseded_chain import mark_superseded

ALLOWED_PATHS: frozenset[str] = frozenset(
    {
        "config/settings.yaml",
        "config/company/**/*.md",
        "config/skills/**/*.yaml",
        "config/modes/**/*.yaml",
        "config/playbooks/**/*.yaml",
        "config/templates/**/*",
        "config/mcp/**/*.yaml",
        "config/prompt_overrides/**/*",
        "config/workstream_overrides.json",
    }
)


def _matches_allowed(target_file: str) -> bool:
    """Check if target_file matches any allowed path/glob pattern."""
    from pathlib import PurePosixPath

    normalized = target_file.replace("\\", "/")
    for pattern in ALLOWED_PATHS:
        if normalized == pattern:
            return True
        if "**" in pattern:
            # e.g. "config/company/**/*.md" → prefix="config/company/", suffix="*.md"
            prefix = pattern.split("**")[0]
            suffix = pattern.split("**")[-1].lstrip("/")
            if normalized.startswith(prefix):
                remainder = normalized[len(prefix) :]
                if not suffix or suffix == "*":
                    return True
                # Check if the filename matches the suffix glob
                from fnmatch import fnmatch

                filename = PurePosixPath(remainder).name
                if fnmatch(filename, suffix) or fnmatch(remainder, suffix):
                    return True
    return False


def _infer_target_kind(target_file: str) -> str:
    """Infer target_kind from file path."""
    parts = target_file.replace("\\", "/").split("/")
    if len(parts) >= 2:
        return parts[1]  # e.g. "company", "skills", "modes"
    return "config"


class AgentModifier:
    """Central orchestrator for agent config modifications."""

    def __init__(
        self,
        session: AsyncSession,
        audit_persistence: AuditPersistence,
        base_path: Path,
        llm_client: LLMClient | None = None,
        mode_settings: ModeAuditSettings | None = None,
    ) -> None:
        self._session = session
        self._audit = audit_persistence
        self._base_path = base_path
        self._llm_client = llm_client
        self._mode_settings = mode_settings

    async def propose_and_apply(
        self,
        tenant_id: UUID,
        target_file: str,
        new_content: str,
        agent_id: str,
        session_id: UUID | None,
        triggered_by: str,
        justification: str | None = None,
    ) -> ModificationResult:
        """Propose and apply a modification. Order: DB → JSONL → file with compensation."""
        if not _matches_allowed(target_file):
            return ModificationResult(
                success=False, record=None, error=f"Path not allowed: {target_file}"
            )

        file_path = self._base_path / target_file
        old_content = file_path.read_text(encoding="utf-8") if file_path.exists() else ""
        diff = compute_diff(old_content, new_content, target_file)
        if not diff:
            return ModificationResult(success=False, record=None, error="No changes detected")

        diff_summary = await generate_summary(diff, self._llm_client)
        needs_approval = requires_approval(target_file, self._mode_settings)
        status = (
            ModificationStatus.PENDING_APPROVAL if needs_approval else ModificationStatus.APPLIED
        )

        record_id = uuid4()
        rollback_token = str(uuid4())
        now = datetime.now(UTC)

        record = ModificationRecord(
            id=record_id,
            tenant_id=tenant_id,
            target_file=target_file,
            target_kind=_infer_target_kind(target_file),
            diff=diff,
            diff_summary=diff_summary,
            applied_at=now,
            rollback_token=rollback_token,
            agent_id=agent_id,
            session_id=session_id,
            triggered_by=triggered_by,
            justification=justification,
            status=status,
        )

        # Step 1: DB commit
        await mark_superseded(tenant_id, target_file, record_id, self._session)
        await self._audit.persist_to_db(record, self._session)
        await self._session.commit()

        # Step 2: JSONL (compensate DB on failure)
        try:
            self._audit.persist_to_jsonl(record)
        except OSError as e:
            await self._session.execute(
                text("DELETE FROM agent_modifications WHERE id = :id"), {"id": record_id}
            )
            await self._session.commit()
            return ModificationResult(success=False, record=None, error=f"JSONL write failed: {e}")

        # Step 3: Write file (only if not pending approval)
        if not needs_approval:
            try:
                _write_file_atomically(file_path, new_content)
            except OSError as e:
                # Compensate: mark as failed in DB
                await self._session.execute(
                    text("UPDATE agent_modifications SET status = 'failed' WHERE id = :id"),
                    {"id": record_id},
                )
                await self._session.commit()
                return ModificationResult(
                    success=False, record=None, error=f"File write failed: {e}"
                )

        # Metrics
        agent_modifications_total.labels(
            target_kind=record.target_kind, triggered_by=triggered_by, status=status.value
        ).inc()
        if needs_approval:
            agent_modifications_pending_approval.labels(tenant_id=str(tenant_id)).inc()

        return ModificationResult(success=True, record=record)

    async def rollback(self, rollback_token: str, user_id: str) -> RollbackResult:
        """Rollback a specific modification by its token."""
        result = await self._session.execute(
            text(
                "SELECT id, tenant_id, target_file, target_kind, diff, status, triggered_by "
                "FROM agent_modifications WHERE rollback_token = :token"
            ),
            {"token": rollback_token},
        )
        row = result.mappings().first()
        if row is None:
            return RollbackResult(success=False, previous_content=None, error="Token not found")

        status = row["status"]
        if status == ModificationStatus.REVERTED.value:
            return RollbackResult(success=False, previous_content=None, error="Already reverted")
        if status == ModificationStatus.PENDING_APPROVAL.value:
            return RollbackResult(
                success=False, previous_content=None, error="Cannot rollback pending approval"
            )

        target_file: str = row["target_file"]  # type: ignore[assignment]
        file_path = self._base_path / target_file
        diff_text: str = row["diff"]  # type: ignore[assignment]

        # Reconstruct expected post-change content and pre-change content from diff
        current_content = file_path.read_text(encoding="utf-8") if file_path.exists() else ""
        old_content, new_content = _reconstruct_from_diff(current_content, diff_text)

        # Conflict detection: current file must match the post-change state
        if current_content != new_content:
            return RollbackResult(
                success=False,
                previous_content=None,
                error="Conflict: file was modified externally after this change",
            )

        # Apply rollback
        _write_file_atomically(file_path, old_content)
        now = datetime.now(UTC)
        await self._session.execute(
            text(
                "UPDATE agent_modifications SET status = 'reverted', "
                "reverted_at = :reverted_at, reverted_by = :reverted_by "
                "WHERE rollback_token = :token"
            ),
            {"reverted_at": now, "reverted_by": user_id, "token": rollback_token},
        )
        await self._session.commit()

        agent_modifications_reverted_total.labels(
            target_kind=row["target_kind"], reason="user_rollback"
        ).inc()

        return RollbackResult(success=True, previous_content=old_content)

    async def approve(self, rollback_token: str, user_id: str) -> ModificationResult:
        """Approve and apply a pending modification."""
        result = await self._session.execute(
            text(
                "SELECT id, tenant_id, target_file, target_kind, diff, diff_summary, "
                "applied_at, rollback_token, agent_id, session_id, triggered_by, "
                "justification, status "
                "FROM agent_modifications WHERE rollback_token = :token"
            ),
            {"token": rollback_token},
        )
        row = result.mappings().first()
        if row is None:
            return ModificationResult(success=False, record=None, error="Token not found")
        if row["status"] != ModificationStatus.PENDING_APPROVAL.value:
            return ModificationResult(success=False, record=None, error="Not pending approval")

        target_file: str = row["target_file"]  # type: ignore[assignment]
        diff_text: str = row["diff"]  # type: ignore[assignment]
        file_path = self._base_path / target_file

        # Apply the change from diff
        old_content = file_path.read_text(encoding="utf-8") if file_path.exists() else ""
        _, new_content = _reconstruct_from_diff(old_content, diff_text)
        _write_file_atomically(file_path, new_content)

        now = datetime.now(UTC)
        await self._session.execute(
            text(
                "UPDATE agent_modifications SET status = 'applied', applied_at = :now "
                "WHERE rollback_token = :token"
            ),
            {"now": now, "token": rollback_token},
        )
        await self._session.commit()

        agent_modifications_pending_approval.labels(tenant_id=str(row["tenant_id"])).dec()

        record = ModificationRecord(
            id=row["id"],  # type: ignore[arg-type]
            tenant_id=row["tenant_id"],  # type: ignore[arg-type]
            target_file=target_file,
            target_kind=row["target_kind"],  # type: ignore[arg-type]
            diff=diff_text,
            diff_summary=row["diff_summary"],  # type: ignore[arg-type]
            applied_at=now,
            rollback_token=rollback_token,
            agent_id=row["agent_id"],  # type: ignore[arg-type]
            session_id=row["session_id"],  # type: ignore[arg-type]
            triggered_by=row["triggered_by"],  # type: ignore[arg-type]
            justification=row["justification"],  # type: ignore[arg-type]
            status=ModificationStatus.APPLIED,
        )
        return ModificationResult(success=True, record=record)

    async def list_pending_approvals(self, tenant_id: UUID) -> list[ModificationRecord]:
        """List all pending approval records for a tenant."""
        from vigilancia_multiagente.enterprise.governance.approval_queue import (
            list_pending_approvals,
        )

        return await list_pending_approvals(tenant_id, self._session)


def _write_file_atomically(path: Path, content: str) -> None:
    """Write content atomically: write to tmp, fsync, rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = tempfile.NamedTemporaryFile(  # noqa: SIM115 - atomic write: close before rename
        mode="w", encoding="utf-8", dir=path.parent, suffix=".tmp", delete=False
    )
    try:
        fd.write(content)
        fd.flush()
        os.fsync(fd.fileno())
        fd.close()
        # On Windows, target must not exist for rename
        if path.exists():
            os.replace(fd.name, str(path))
        else:
            os.rename(fd.name, str(path))
    except BaseException:
        fd.close()
        if os.path.exists(fd.name):
            os.unlink(fd.name)
        raise


def _reconstruct_from_diff(current_content: str, diff_text: str) -> tuple[str, str]:
    """From a unified diff, reconstruct old_content and new_content.

    Uses the diff hunks to reverse-engineer the before/after states.
    old_content = content before the change (lines starting with - or context)
    new_content = content after the change (lines starting with + or context)
    """
    old_lines: list[str] = []
    new_lines: list[str] = []
    in_hunk = False

    for line in diff_text.splitlines(keepends=True):
        if line.startswith(("---", "+++")):
            continue
        if line.startswith("@@"):
            in_hunk = True
            continue
        if not in_hunk:
            continue
        if line.startswith("-"):
            old_lines.append(line[1:])
        elif line.startswith("+"):
            new_lines.append(line[1:])
        else:
            # Context line (starts with space)
            text_line = line[1:] if line.startswith(" ") else line
            old_lines.append(text_line)
            new_lines.append(text_line)

    return "".join(old_lines), "".join(new_lines)
