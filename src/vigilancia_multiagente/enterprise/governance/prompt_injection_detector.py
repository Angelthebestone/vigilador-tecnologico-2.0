"""PromptInjectionDetector — detección PI por regex + dataset Lakera (FR-001..FR-005)."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Literal

from vigilancia_multiagente.enterprise.governance.detection_result import DetectionResult

logger = logging.getLogger(__name__)

_CHUNK_SIZE = 100_000  # 100KB chunks (EC-02)

# FR-002: heurísticas regex hardcoded (inglés + español)
_BUILTIN_PATTERNS: list[tuple[str, str, int]] = [
    (r"ignore\s+(all\s+)?previous\s+instructions", "control_flow", 3),
    (r"system\s*:", "system_prompt", 2),
    (r"you\s+are\s+now", "identity_manipulation", 3),
    (r"disregard\s+(the\s+)?(above|previous)", "control_flow", 3),
    (r"forget\s+(everything|all|your\s+instructions)", "control_flow", 3),
    (r"new\s+instructions?\s*:", "control_flow", 2),
    (r"override\s*:", "control_flow", 2),
    (r"act\s+as\s+if", "identity_manipulation", 2),
    (r"pretend\s+you\s+are", "identity_manipulation", 2),
    (r"ignora\s+(las\s+)?instrucciones\s+(anteriores|previas)", "control_flow_es", 3),
    (r"olvida\s+(todo|tus\s+instrucciones)", "control_flow_es", 3),
    (r"nuevas\s+instrucciones\s*:", "control_flow_es", 2),
    (r"ahora\s+eres\s+un", "identity_manipulation_es", 3),
]

_EXFILTRATION_CATEGORIES = frozenset({"exfiltration", "evasion"})


class PromptInjectionDetector:
    """Detector de prompt injection por regex + patrones Lakera."""

    def __init__(self, lakera_path: Path | None = None) -> None:
        self._compiled: list[tuple[re.Pattern[str], str, int]] = []
        self._load_builtin()
        self._load_lakera(lakera_path)

    def _load_builtin(self) -> None:
        for pattern, category, weight in _BUILTIN_PATTERNS:
            self._compiled.append((re.compile(pattern, re.IGNORECASE), category, weight))

    def _load_lakera(self, lakera_path: Path | None) -> None:
        path = lakera_path or Path("config/security/lakera-patterns.json")
        if not path.exists():
            logger.warning(
                "Lakera patterns file not found at %s; operating with regex-only mode (EC-05)",
                path,
            )
            return
        raw = path.read_text(encoding="utf-8")
        entries: list[dict[str, object]] = json.loads(raw)
        for entry in entries:
            pattern_str = str(entry["pattern"])
            category = str(entry["category"])
            weight = int(entry["severity_weight"])  # type: ignore[arg-type]
            self._compiled.append((re.compile(pattern_str, re.IGNORECASE), category, weight))

    def detect(self, content: str, source: str) -> DetectionResult:
        """Analiza contenido y retorna resultado de detección (FR-004)."""
        matched_patterns: list[str] = []
        matched_categories: set[str] = set()
        max_weight = 0

        for chunk_start in range(0, max(len(content), 1), _CHUNK_SIZE):
            chunk = content[chunk_start : chunk_start + _CHUNK_SIZE]
            for compiled_re, category, weight in self._compiled:
                if compiled_re.search(chunk):
                    pattern_label = f"{category}:{compiled_re.pattern}"
                    if pattern_label not in matched_patterns:
                        matched_patterns.append(pattern_label)
                        matched_categories.add(category)
                        if weight > max_weight:
                            max_weight = weight

        if not matched_patterns:
            return DetectionResult(
                is_suspicious=False,
                patterns_matched=[],
                severity="LOW",
                confidence=0.0,
                source=source,
            )

        severity = self._compute_severity(matched_patterns, matched_categories)
        confidence = min(1.0, len(matched_patterns) * 0.3 + max_weight * 0.1)

        return DetectionResult(
            is_suspicious=True,
            patterns_matched=matched_patterns,
            severity=severity,
            confidence=confidence,
            source=source,
        )

    def _compute_severity(
        self, patterns: list[str], categories: set[str]
    ) -> Literal["LOW", "MEDIUM", "HIGH"]:
        """FR-005: HIGH si >=2 patrones o exfiltración; MEDIUM si 1 control; LOW si ambiguo."""
        has_exfiltration = bool(categories & _EXFILTRATION_CATEGORIES)
        if has_exfiltration or len(patterns) >= 2:
            return "HIGH"
        # Single pattern — check if it's a control flow pattern
        for cat in categories:
            if "control_flow" in cat or "identity_manipulation" in cat or "system_prompt" in cat:
                return "MEDIUM"
        return "LOW"
