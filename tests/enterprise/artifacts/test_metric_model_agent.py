"""Tests for MetricModelAgent (T006 — FR-003, FR-007, EC-02)."""

from __future__ import annotations

from vigilancia_multiagente.enterprise.artifacts.metric_model_agent import MetricModelAgent
from vigilancia_multiagente.enterprise.artifacts.ports import DataSource


def _make_sources(*names: str) -> tuple[DataSource, ...]:
    return tuple(
        DataSource(name=n, source_type="CSV", location=f"/data/{n}", available=True) for n in names
    )


def test_kpis_generated_with_complete_fields() -> None:
    """KPIs generados con nombre/formula/fuente/granularidad/formato."""
    agent = MetricModelAgent()
    sources = _make_sources("ventas.csv", "clientes.csv")
    kpis_input = [
        {
            "name": "Ventas Totales",
            "formula": "SUM(monto)",
            "source": "ventas.csv",
            "granularity": "mensual",
            "display_format": "bar_chart",
        },
        {
            "name": "Clientes Nuevos",
            "formula": "COUNT(id)",
            "source": "clientes.csv",
            "granularity": "semanal",
            "display_format": "line_chart",
        },
    ]

    result = agent.model_metrics("dashboard de ventas", sources, kpis_input)

    assert len(result.kpis) == 2
    for kpi in result.kpis:
        assert kpi.name
        assert kpi.formula
        assert kpi.source
        assert kpi.granularity
        assert kpi.display_format
    assert result.refresh_policy in ("diario", "manual")


def test_data_gap_detected_and_reported() -> None:
    """Brecha de datos detectada y reportada (EC-02)."""
    agent = MetricModelAgent()
    sources = _make_sources("ventas.csv")
    kpis_input = [
        {
            "name": "Margen",
            "formula": "SUM(ganancia)/SUM(costo)",
            "source": "costos.csv",
            "granularity": "mensual",
            "display_format": "gauge",
        },
    ]

    result = agent.model_metrics("dashboard financiero", sources, kpis_input)

    assert len(result.gaps) == 1
    assert "costos.csv" in result.gaps[0]
    assert "Brechas detectadas" in result.message


def test_vague_request_asks_clarification() -> None:
    """Solicitud sin métricas claras pide clarificación."""
    agent = MetricModelAgent()
    sources = _make_sources("data.csv")

    result = agent.model_metrics("KPI", sources)

    assert len(result.kpis) == 0
    assert "especifique" in result.message.lower() or "claras" in result.message.lower()


def test_refresh_policy_declared_per_artifact() -> None:
    """refresh_policy declarada por artefacto (FR-007)."""
    agent = MetricModelAgent()
    sources = _make_sources("ventas.csv", "inventario.csv")
    kpis_input = [
        {
            "name": "Stock",
            "formula": "SUM(cantidad)",
            "source": "inventario.csv",
            "granularity": "diario",
            "display_format": "table",
        },
    ]

    result = agent.model_metrics("dashboard de inventario con refresh diario", sources, kpis_input)

    assert result.refresh_policy
    assert result.refresh_policy in ("diario", "manual", "cada 15 minutos")
