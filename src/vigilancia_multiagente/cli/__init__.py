"""CLI package for vigilancia_multiagente."""

from __future__ import annotations

import click

from vigilancia_multiagente.cli.audit_commands import audit


@click.group()
def main() -> None:
    """Vigilador admin CLI."""


main.add_command(audit)
