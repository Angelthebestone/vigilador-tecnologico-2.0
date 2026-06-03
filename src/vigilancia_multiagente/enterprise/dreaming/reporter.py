"""Dreaming reporter — writes per-cycle JSONL completion reports (Spec 021 F5a.A / T126).

Single responsibility: take a :class:`CycleReport` from the orchestrator
and append it as a JSON line to the daily file
``~/.vigilador/audit/dreaming/<YYYY-MM-DD>.jsonl``. The full Dreaming
Report (HTML/markdown summarisation) is on the F5b roadmap; the MVP
keeps it to a structured machine-readable line per cycle so cron jobs
can be monitored without hand-built dashboards.

Constitución:
* SRP: one job — JSONL persistence of a cycle outcome. The orchestrator
  delegates here so the orchestrator class stays focused on phase
  execution / pause-resume.
* DIP: the orchestrator depends on a callable port (see
  :class:`ReporterPort`), tests inject fakes.
* #4 explicit: invalid audit dirs raise ``ReporterError`` rather than
  swallowing IO errors silently.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from vigilancia_multiagente.enterprise.dreaming.models import CycleReport

logger = logging.getLogger(__name__)


_DEFAULT_AUDIT_DIR = Path.home() / ".vigilador" / "audit" / "dreaming"


class ReporterError(RuntimeError):
    """Raised when the reporter cannot persist a cycle report."""


class ReporterPort(Protocol):
    """Port the orchestrator depends on (tests inject fakes)."""

    def report(self, report: CycleReport) -> Path: ...


@dataclass
class DreamingReporter:
    """Append-only JSONL reporter for completed dreaming cycles.

    ``audit_dir`` is created on first ``report()`` call. Rotation by date
    is implicit: the file name embeds the cycle's ``started_at`` date.
    """

    audit_dir: Path = _DEFAULT_AUDIT_DIR

    def report(self, report: CycleReport) -> Path:
        """Append a JSON line and return the file written.

        Raises :class:`ReporterError` if the directory cannot be created
        or the line cannot be written. The orchestrator is expected to
        log + continue rather than abort the whole cycle.
        """
        try:
            self.audit_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise ReporterError(
                f"Cannot create audit directory {self.audit_dir}: {exc}"
            ) from exc

        date_str = report.started_at.strftime("%Y-%m-%d")
        path = self.audit_dir / f"{date_str}.jsonl"
        entry = {
            "cycle_id": report.cycle_id,
            "started_at": report.started_at.isoformat(),
            "finished_at": report.finished_at.isoformat(),
            "results": [
                {
                    "phase": r.phase_name,
                    "status": r.status.value,
                    "duration_ms": round(r.duration_ms, 2),
                    "error": r.error,
                }
                for r in report.results
            ],
        }
        try:
            with path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError as exc:
            raise ReporterError(
                f"Cannot write cycle report to {path}: {exc}"
            ) from exc

        logger.info(
            "Dreaming cycle %s reported (%d phases) → %s",
            report.cycle_id,
            len(report.results),
            path,
        )
        return path
