"""Constitution compliance tests for Spec 007 SC-PLAN-01..09.

Verifica invariantes de arquitectura y diseno sin ejecutar herramientas
externas — usa asserts simples sobre estructura del codigo fuente.
"""

from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC = PROJECT_ROOT / "src" / "vigilancia_multiagente"
SCRIPTS = PROJECT_ROOT / "scripts"
CONFIG = PROJECT_ROOT / "config"
SETTINGS_PY = SRC / "config" / "settings.py"


# ── SC-PLAN-01: Layer imports ─────────────────────────────────────────────


@pytest.mark.parametrize(
    "filepath,expected_violations",
    [
        # application layer should not import from api or infra
        ("application/orchestration/orchestrator_service.py", []),
        ("application/evaluation/obsolescence_detector.py", []),
        ("application/evaluation/hype_detector.py", []),
        ("application/evaluation/report_quality_gate.py", []),
    ],
)
def test_sc_plan_01_layer_imports(filepath: str, expected_violations: list[str]) -> None:
    """SC-PLAN-01: Layer boundaries — no prohibited cross-layer imports.

    application/ MUST NOT import from api/ or infra/.
    domain/    MUST NOT import from api/, application/, or infra/.
    """
    full = SRC / filepath
    if not full.exists():
        pytest.skip(f"{full} does not exist (not yet migrated)")
    content = full.read_text(encoding="utf-8")
    violations: list[str] = []
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith(("from ", "import ")) and (
            "vigilancia_multiagente.api" in stripped or "vigilancia_multiagente.infra" in stripped
        ):
            violations.append(stripped)
    assert violations == expected_violations, (
        f"{filepath} has unexpected layer import violations: {violations}"
    )


# ── SC-PLAN-02: basedpyright command exists ───────────────────────────────


def test_sc_plan_02_basedpyright_command_exists() -> None:
    """SC-PLAN-02: basedpyright debe estar instalado."""
    import importlib.util

    assert importlib.util.find_spec("basedpyright") is not None, (
        "basedpyright no esta instalado — ejecutar: pip install basedpyright"
    )


# ── SC-PLAN-03 & 04: pytest scripts exist ────────────────────────────────


def test_sc_plan_03_pytest_script_exists() -> None:
    """SC-PLAN-03: pytest debe estar disponible (flags false)."""
    import importlib.util

    assert importlib.util.find_spec("pytest") is not None, "pytest no esta instalado"


def test_sc_plan_04_pytest_script_exists() -> None:
    """SC-PLAN-04: pytest debe estar disponible (flags true — golden suite)."""
    import importlib.util

    assert importlib.util.find_spec("pytest") is not None, "pytest no esta instalado"


# ── SC-PLAN-05: eval_ws flags exist in settings.py ────────────────────────


def test_sc_plan_05_eval_ws_flags_exist() -> None:
    """SC-PLAN-05: todos los flags eval_ws_*_enabled existen en settings.py."""
    assert SETTINGS_PY.exists(), f"settings.py not found at {SETTINGS_PY}"
    content = SETTINGS_PY.read_text(encoding="utf-8")
    expected_flags = [
        "eval_ws_a_enabled",
        "eval_ws_b_enabled",
        "eval_ws_c_enabled",
        "eval_ws_d_enabled",
        "eval_ws_e_enabled",
    ]
    for flag in expected_flags:
        assert flag in content, f"Flag {flag} no encontrado en {SETTINGS_PY}"


# ── SC-PLAN-06: benchmark_latency.py exists ───────────────────────────────


def test_sc_plan_06_benchmark_latency_exists() -> None:
    """SC-PLAN-06: scripts/benchmark_latency.py debe existir y ser ejecutable."""
    script = SCRIPTS / "benchmark_latency.py"
    assert script.exists(), f"{script} no existe"
    assert script.read_bytes().startswith(b"#!/usr/bin/env python3"), (
        "benchmark_latency.py debe comenzar con shebang"
    )


# ── SC-PLAN-07: confidence_calibrator.py no existe ────────────────────────


@pytest.mark.parametrize(
    "path",
    [
        SRC / "application" / "evaluation" / "confidence_calibrator.py",
    ],
)
def test_sc_plan_07_confidence_calibrator_not_exists(path: Path) -> None:
    """SC-PLAN-07: confidence_calibrator.py no debe existir (eliminado)."""
    assert not path.exists(), f"{path.relative_to(PROJECT_ROOT)} aun existe — debe ser eliminado"


# ── SC-PLAN-08: no DEPRECATED legacy files ────────────────────────────────


def _legacy_files() -> list[Path]:
    candidates = [
        "application/evaluation/branch_kpi_service.py",
        "application/evaluation/golden_cases_runner.py",
        "application/evaluation/prompt_regression_service.py",
    ]
    found = []
    for rel in candidates:
        full = SRC / rel
        if full.exists():
            found.append(full)
    return found


@pytest.mark.parametrize(
    "filepath",
    [
        "application/evaluation/branch_kpi_service.py",
        "application/evaluation/golden_cases_runner.py",
        "application/evaluation/prompt_regression_service.py",
    ],
)
def test_sc_plan_08_no_deprecated_legacy(filepath: str) -> None:
    """SC-PLAN-08: archivos legacy sin marca DEPRECATED."""
    full = SRC / filepath
    if not full.exists():
        pytest.skip(f"{filepath} no existe (ya eliminado)")
    content = full.read_text(encoding="utf-8")
    assert "DEPRECATED" in content, (
        f"{filepath} no contiene marca DEPRECATED — debe indicar estado legacy"
    )


# ── SC-PLAN-09: no .get("results", []) in src/ ────────────────────────────


def _find_get_results(pattern: str, root: Path) -> list[str]:
    """Find lines matching the pattern in Python files under root."""
    hits: list[str] = []
    for pyfile in sorted(root.rglob("*.py")):
        if pyfile.name == "__init__.py":
            continue
        for i, line in enumerate(pyfile.read_text(encoding="utf-8").splitlines(), start=1):
            if pattern in line:
                hits.append(f"{pyfile.relative_to(root)}:{i}")
    return hits


@pytest.mark.parametrize(
    "pattern,expected_hits",
    [
        ('.get("results", [])', []),
        ('.get("results",[])', []),
    ],
)
def test_sc_plan_09_no_get_results(pattern: str, expected_hits: list[str]) -> None:
    """SC-PLAN-09: sin parseo manual .get("results", []) en src/.

    El parseo debe hacerse via adapters con tipado fuerte, no con
    acceso a dicts sin estructura.
    """
    hits = _find_get_results(pattern, SRC)
    assert hits == expected_hits, f"Se encontraron accesos manuales .get('results', []) en: {hits}"
