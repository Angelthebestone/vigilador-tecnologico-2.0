"""PipelinePlanner — generates technical data flow plan (FR-004, helper for coordinator)."""

from __future__ import annotations

from vigilancia_multiagente.enterprise.artifacts.ports import (
    DataSource,
    KPIDefinition,
    PipelinePlan,
)


class PipelinePlanner:
    """Helper that generates a technical pipeline plan from sources and KPIs.

    Not an autonomous agent — used internally by ArtifactCoordinator.
    """

    def plan(
        self,
        sources: tuple[DataSource, ...],
        kpis: tuple[KPIDefinition, ...],
        refresh_policy: str,
    ) -> PipelinePlan:
        """Generate pipeline plan connecting sources to KPI visualizations.

        Args:
            sources: Available data sources.
            kpis: Defined KPI metrics.
            refresh_policy: Declared refresh frequency.

        Returns:
            PipelinePlan with steps, transformations, and refresh policy.
        """
        steps: list[str] = []
        transformations: list[str] = []

        # Step 1: Extract from each source
        for source in sources:
            if source.available:
                steps.append(f"extract:{source.name}:{source.source_type}")

        # Step 2: Transform for each KPI
        for kpi in kpis:
            transformations.append(f"compute:{kpi.name}:{kpi.formula}")
            steps.append(f"transform:{kpi.name}")

        # Step 3: Load into visualization
        steps.append("load:visualization")

        return PipelinePlan(
            steps=tuple(steps),
            transformations=tuple(transformations),
            refresh_policy=refresh_policy,
        )
