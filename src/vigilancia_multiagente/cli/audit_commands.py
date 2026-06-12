"""CLI commands for audit trail management."""

from __future__ import annotations

import asyncio
from datetime import datetime
from uuid import UUID

import click

from vigilancia_multiagente.enterprise.governance.agent_modifier import AgentModifier
from vigilancia_multiagente.enterprise.governance.audit_persistence import AuditPersistence
from vigilancia_multiagente.infra.db.connection import database
from vigilancia_multiagente.infra.persistence.agent_modifications_repository import (
    AgentModificationsRepository,
)


def _run(coro):  # type: ignore[no-untyped-def]
    """Run an async coroutine synchronously."""
    return asyncio.run(coro)


@click.group()
def audit() -> None:
    """Audit trail commands."""


@audit.command()
@click.option("--since", type=click.DateTime(), default=None, help="Filter from date")
@click.option("--tenant", type=str, required=True, help="Tenant UUID")
def changelog(since: datetime | None, tenant: str) -> None:
    """List recent modifications."""

    async def _run_changelog() -> None:
        async with database.session() as session:
            repo = AgentModificationsRepository(session)
            records = await repo.list_changelog(UUID(tenant), since=since)
        for r in records:
            summary = r.diff_summary or "(no summary)"
            click.echo(
                f"{r.applied_at:%Y-%m-%d %H:%M} | {r.target_file} | {summary} | "
                f"{r.triggered_by} | {r.agent_id} | {r.status.value}"
            )

    _run(_run_changelog())


@audit.command()
@click.argument("token")
def show(token: str) -> None:
    """Show full diff for a modification."""

    async def _run_show() -> None:
        async with database.session() as session:
            repo = AgentModificationsRepository(session)
            record = await repo.get_by_token(token)
        if record is None:
            click.echo(f"Error: token '{token}' not found", err=True)
            raise SystemExit(1)
        click.echo(f"File: {record.target_file}")
        click.echo(f"Status: {record.status.value}")
        click.echo(f"Applied: {record.applied_at}")
        click.echo(f"Agent: {record.agent_id}")
        click.echo("--- Diff ---")
        click.echo(record.diff)

    _run(_run_show())


@audit.command(name="pending-approvals")
def pending_approvals() -> None:
    """List modifications pending approval."""

    async def _run_pending() -> None:
        from sqlalchemy import text as sql_text

        async with database.session() as session:
            result = await session.execute(
                sql_text(
                    "SELECT rollback_token, target_file, applied_at, agent_id "
                    "FROM agent_modifications WHERE status = 'pending_approval' "
                    "ORDER BY applied_at DESC"
                )
            )
            rows = result.mappings().all()
        if not rows:
            click.echo("No pending approvals.")
            return
        for row in rows:
            click.echo(
                f"{row['applied_at']:%Y-%m-%d %H:%M} | {row['target_file']} | "
                f"token={row['rollback_token']} | agent={row['agent_id']}"
            )

    _run(_run_pending())


@audit.command(name="rollback")
@click.argument("token")
@click.option("--user", type=str, default="admin", help="User performing rollback")
@click.option(
    "--base-path", type=click.Path(exists=True), default=".", help="Base path for config files"
)
def rollback_cmd(token: str, user: str, base_path: str) -> None:
    """Rollback a specific modification."""
    from pathlib import Path

    async def _run_rollback() -> None:
        async with database.session() as session:
            modifier = AgentModifier(
                session=session,
                audit_persistence=AuditPersistence(),
                base_path=Path(base_path),
            )
            result = await modifier.rollback(token, user)
        if result.success:
            click.echo(f"Rollback successful for token {token}")
        else:
            click.echo(f"Rollback failed: {result.error}", err=True)
            raise SystemExit(1)

    _run(_run_rollback())


@audit.command()
@click.argument("token")
@click.option("--user", type=str, default="admin", help="User approving")
@click.option(
    "--base-path", type=click.Path(exists=True), default=".", help="Base path for config files"
)
def approve(token: str, user: str, base_path: str) -> None:
    """Approve a pending modification."""
    from pathlib import Path

    async def _run_approve() -> None:
        async with database.session() as session:
            modifier = AgentModifier(
                session=session,
                audit_persistence=AuditPersistence(),
                base_path=Path(base_path),
            )
            result = await modifier.approve(token, user)
        if result.success:
            click.echo(f"Approved and applied: {token}")
        else:
            click.echo(f"Approve failed: {result.error}", err=True)
            raise SystemExit(1)

    _run(_run_approve())
