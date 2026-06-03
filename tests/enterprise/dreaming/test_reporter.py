"""F5a.A / T126 — DreamingReporter JSONL tests."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from vigilancia_multiagente.enterprise.dreaming.models import (
    CycleReport,
    PhaseResult,
    PhaseStatus,
)
from vigilancia_multiagente.enterprise.dreaming.reporter import (
    DreamingReporter,
    ReporterError,
)


def _make_report(cycle_id: str = "abc123") -> CycleReport:
    started = datetime(2026, 1, 15, 3, 0, tzinfo=UTC)
    finished = datetime(2026, 1, 15, 3, 1, tzinfo=UTC)
    return CycleReport(
        cycle_id=cycle_id,
        started_at=started,
        finished_at=finished,
        results=[
            PhaseResult(
                phase_name="memory_consolidation",
                status=PhaseStatus.SUCCESS,
                duration_ms=1234.5,
            ),
            PhaseResult(
                phase_name="ingestion_sync",
                status=PhaseStatus.SUCCESS,
                duration_ms=87.6,
            ),
        ],
    )


def test_reporter_writes_jsonl_to_dated_file(tmp_path: Path) -> None:
    reporter = DreamingReporter(audit_dir=tmp_path)
    report = _make_report()
    written = reporter.report(report)
    assert written == tmp_path / "2026-01-15.jsonl"
    lines = written.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["cycle_id"] == "abc123"
    assert {p["phase"] for p in payload["results"]} == {
        "memory_consolidation",
        "ingestion_sync",
    }


def test_reporter_appends_multiple_cycles_same_day(tmp_path: Path) -> None:
    reporter = DreamingReporter(audit_dir=tmp_path)
    reporter.report(_make_report("first"))
    reporter.report(_make_report("second"))
    lines = (tmp_path / "2026-01-15.jsonl").read_text(encoding="utf-8").splitlines()
    assert [json.loads(line)["cycle_id"] for line in lines] == ["first", "second"]


def test_reporter_creates_audit_dir_if_missing(tmp_path: Path) -> None:
    nested = tmp_path / "deep" / "audit" / "dreaming"
    reporter = DreamingReporter(audit_dir=nested)
    reporter.report(_make_report())
    assert (nested / "2026-01-15.jsonl").exists()


def test_reporter_raises_when_dir_cannot_be_created(monkeypatch, tmp_path: Path) -> None:
    reporter = DreamingReporter(audit_dir=tmp_path / "nope")

    def boom(self, *args, **kwargs):
        raise OSError("simulated mkdir failure")

    monkeypatch.setattr(Path, "mkdir", boom)
    with pytest.raises(ReporterError, match="Cannot create audit directory"):
        reporter.report(_make_report())
