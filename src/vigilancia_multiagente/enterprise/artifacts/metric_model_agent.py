# ROADMAP F5b - fuera de MVP 021; no registrar en runtime
"""MetricModelAgent — models KPIs from sources and user request (FR-003, FR-007)."""

from __future__ import annotations

from dataclasses import dataclass

from vigilancia_multiagente.enterprise.artifacts.ports import DataSource, KPIDefinition


@dataclass(frozen=True)
class MetricModelResult:
    """Result of metric modeling phase."""

    kpis: tuple[KPIDefinition, ...]
    refresh_policy: str
    gaps: tuple[str, ...]
    message: str


class MetricModelAgent:
    """Defines KPIs and data contracts from user request and available sources."""

    def model_metrics(
        self,
        request: str,
        sources: tuple[DataSource, ...],
        requested_kpis: list[dict[str, str]] | None = None,
    ) -> MetricModelResult:
        """Generate KPI definitions from request and available sources.

        Args:
            request: User's natural language request.
            sources: Available data sources from inventory.
            requested_kpis: Optional explicit KPI definitions from user.

        Returns:
            MetricModelResult with KPIs, refresh policy, and any data gaps.

        Raises:
            ValueError: If request is empty or no metrics can be inferred.
        """
        if not request.strip():
            raise ValueError("La solicitud no puede estar vacía para modelar métricas.")

        if not sources:
            raise ValueError(
                "No hay fuentes disponibles. Ejecute el inventario de fuentes primero."
            )

        available_sources = [s for s in sources if s.available]
        if not available_sources:
            return MetricModelResult(
                kpis=(),
                refresh_policy="manual",
                gaps=tuple(s.name for s in sources),
                message="Todas las fuentes están no disponibles. No se pueden modelar KPIs.",
            )

        # Build KPIs from explicit definitions or infer from request
        kpis: list[KPIDefinition] = []
        gaps: list[str] = []

        if requested_kpis:
            for kpi_def in requested_kpis:
                source_name = kpi_def.get("source", "")
                source_available = any(s.name == source_name for s in available_sources)
                if not source_available and source_name:
                    gaps.append(
                        f"Datos requeridos para '{kpi_def.get('name', '?')}' "
                        f"no disponibles en fuente '{source_name}'"
                    )
                    continue
                kpis.append(
                    KPIDefinition(
                        name=kpi_def.get("name", "KPI sin nombre"),
                        formula=kpi_def.get("formula", "SUM(valor)"),
                        source=source_name or available_sources[0].name,
                        granularity=kpi_def.get("granularity", "mensual"),
                        display_format=kpi_def.get("display_format", "bar_chart"),
                    )
                )
        else:
            # Clarification needed if no explicit KPIs and request is too vague
            if len(request.split()) < 3:
                return MetricModelResult(
                    kpis=(),
                    refresh_policy="manual",
                    gaps=(),
                    message=(
                        "La solicitud no contiene métricas claras. "
                        "Por favor especifique qué KPIs desea visualizar."
                    ),
                )
            # Default: create a single KPI from the request
            kpis.append(
                KPIDefinition(
                    name=f"KPI: {request[:50]}",
                    formula="SUM(valor)",
                    source=available_sources[0].name,
                    granularity="mensual",
                    display_format="bar_chart",
                )
            )

        refresh_policy = "diario" if len(available_sources) > 1 else "manual"

        if gaps:
            msg = f"Modelo generado con {len(kpis)} KPI(s). Brechas detectadas: {len(gaps)}."
        else:
            msg = f"Modelo generado exitosamente con {len(kpis)} KPI(s)."

        return MetricModelResult(
            kpis=tuple(kpis),
            refresh_policy=refresh_policy,
            gaps=tuple(gaps),
            message=msg,
        )
