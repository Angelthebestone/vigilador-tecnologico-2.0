"""Prompt-injection quarantine JSONL writer (Spec 021 F5a.C / T132).

Single responsibility: append one JSON line per quarantine event to
``~/.vigilador/audit/pi_quarantine_<YYYY-MM-DD>.jsonl``. The DB-backed
:class:`...governance.pi_quarantine_repository.PIQuarantineRepository`
covers durable enterprise persistence; this module is the lightweight
filesystem audit channel that the spec mandates for MVP visibility
without requiring a database connection (FR-044).

Constitución:
* SRP: append-only JSONL writer, no DB / no detection logic.
* DIP: callers depend on the :class:`PIQuarantineWriterPort` Protocol;
  the default :class:`PIQuarantineJSONLWriter` is one implementation.
* #4 explicit: IO failures raise :class:`PIQuarantineWriterError` with
  full context; the caller decides whether to continue.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from vigilancia_multiagente.enterprise.governance.detection_result import DetectionResult

logger = logging.getLogger(__name__)


_DEFAULT_AUDIT_DIR = Path.home() / ".vigilador" / "audit"
_FILE_PREFIX = "pi_quarantine_"


class PIQuarantineWriterError(RuntimeError):
    """Raised when the writer cannot persist a quarantine event."""


class PIQuarantineWriterPort(Protocol):
    """Port the ingestion / connector layers depend on."""

    def write(
        self,
        result: DetectionResult,
        content_excerpt: str,
        tenant_id: str | None = None,
        ref_id: str | None = None,
    ) -> Path: ...


@dataclass
class PIQuarantineJSONLWriter:
    """Daily-rotated JSONL writer for PI quarantine events."""

    audit_dir: Path = _DEFAULT_AUDIT_DIR
    excerpt_max_chars: int = 500

    def write(
        self,
        result: DetectionResult,
        content_excerpt: str,
        tenant_id: str | None = None,
        ref_id: str | None = None,
    ) -> Path:
        """Append a single JSON line representing the quarantine event.

        Returns the file written. Raises :class:`PIQuarantineWriterError`
        on disk failure. The caller is expected to have already verified
        ``result.is_suspicious`` — calling on a clean detection still
        writes a line so that audit logs can answer "did the detector
        run for this content?". This matches the F5a.C requirement that
        EVERY detection (positive or negative) be auditable.
        """
        try:
            self.audit_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise PIQuarantineWriterError(
                f"Cannot create audit directory {self.audit_dir}: {exc}"
            ) from exc

        now = datetime.now(UTC)
        date_str = now.strftime("%Y-%m-%d")
        path = self.audit_dir / f"{_FILE_PREFIX}{date_str}.jsonl"
        entry = {
            "timestamp": now.isoformat(),
            "tenant_id": tenant_id,
            "ref_id": ref_id,
            "source": result.source,
            "is_suspicious": result.is_suspicious,
            "severity": result.severity,
            "confidence": round(result.confidence, 3),
            "patterns_matched": result.patterns_matched,
            "content_excerpt": content_excerpt[: self.excerpt_max_chars],
        }
        try:
            with path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
                fh.flush()
                os.fsync(fh.fileno())
        except OSError as exc:
            raise PIQuarantineWriterError(
                f"Cannot write quarantine entry to {path}: {exc}"
            ) from exc

        if result.is_suspicious:
            logger.warning(
                "PI quarantined: source=%s severity=%s patterns=%d → %s",
                result.source,
                result.severity,
                len(result.patterns_matched),
                path,
            )
        return path
