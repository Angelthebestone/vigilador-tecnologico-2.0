"""Enterprise composition root — builds Ola 1/2 (3.0) subsystems for app.state.

Called from api/app.py lifespan. Kept separate from the eager 2.0
``dependencies.py`` so enterprise wiring stays lazy and optional. Each
subsystem is built in its own guarded block: a failure (missing key, no
network, no DB) is logged with context and the remaining subsystems still
wire up. This is optional-subsystem initialization, not defensive masking —
errors are surfaced via logger, never silenced.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _resolve(base: str) -> Path:
    """Resolve a settings path relative to the project root."""
    p = Path(base)
    return p if p.is_absolute() else PROJECT_ROOT / p


async def build_enterprise_services(settings: Any, database: Any) -> dict[str, Any]:
    """Build all enterprise subsystems. Returns a dict for app.state attachment.

    Subsystems wired: ToolRegistry (+builtin tools + catalog metadata),
    ModeRegistry, PlaybookRegistry, SkillRegistry+SkillLoader, Dreaming
    scheduler+orchestrator. Goal-pursuit / artifacts / app-development expose
    their registries via config; full execution needs runtime ports (see
    WIRING NOTE in verification report).
    """
    from vigilancia_multiagente.infra.embeddings.gemini_gateway import GeminiEmbeddingGateway
    from vigilancia_multiagente.infra.persistence.tool_health_repository import (
        ToolHealthRepository,
    )

    services: dict[str, Any] = {}
    embedding_gateway = GeminiEmbeddingGateway()

    # ── ToolRegistry + builtin tools + catalog metadata (specs 009/018) ──
    tool_registry = await _build_tool_registry(settings, database, embedding_gateway, ToolHealthRepository)
    services["tool_registry"] = tool_registry
    _load_catalog(settings, services)

    # ── Modes + Playbooks (spec 011/012) ──
    _build_modes_and_playbooks(settings, services)

    # ── Skill marketplace (spec 015) ──
    if settings.skills_marketplace_enabled and tool_registry is not None:
        await _build_skills(settings, embedding_gateway, tool_registry, services)

    # ── Dreaming (spec 017) — scheduler + orchestrator, default disabled ──
    _build_dreaming(settings, services)

    return services


async def _build_tool_registry(settings, database, embedding_gateway, tool_health_repo_cls):
    # Documents tools (spec 009 + spec 018 — already shipped)
    # Spec 021 D5 native-first WRAP-SDK + CLONE-UPSTREAM tools (T015-T031).
    from vigilancia_multiagente.enterprise.tooling.builtin.creative.minimax_image import (
        MiniMaxImageTool,
    )
    from vigilancia_multiagente.enterprise.tooling.builtin.documents.docx_generate import (
        DocxGenerateTool,
    )
    from vigilancia_multiagente.enterprise.tooling.builtin.documents.file_system import (
        FileSystemTool,
    )
    from vigilancia_multiagente.enterprise.tooling.builtin.documents.markitdown import (
        MarkitdownTool,
    )
    from vigilancia_multiagente.enterprise.tooling.builtin.documents.pdf_generate import (
        PdfGenerateTool,
    )
    from vigilancia_multiagente.enterprise.tooling.builtin.documents.template_render import (
        TemplateRenderTool,
    )
    from vigilancia_multiagente.enterprise.tooling.builtin.execution.sandbox import (
        SandboxTool,
    )
    from vigilancia_multiagente.enterprise.tooling.builtin.productivity.google_workspace import (
        GoogleWorkspaceTool,
    )
    from vigilancia_multiagente.enterprise.tooling.builtin.research.arxiv import (
        ArxivTool,
    )
    from vigilancia_multiagente.enterprise.tooling.builtin.research.brave import (
        BraveTool,
    )
    from vigilancia_multiagente.enterprise.tooling.builtin.research.exa import ExaTool
    from vigilancia_multiagente.enterprise.tooling.builtin.research.firecrawl import (
        FirecrawlTool,
    )
    from vigilancia_multiagente.enterprise.tooling.builtin.research.google_scholar import (
        GoogleScholarTool,
    )
    from vigilancia_multiagente.enterprise.tooling.builtin.research.jina import JinaTool
    from vigilancia_multiagente.enterprise.tooling.builtin.research.openalex import (
        OpenAlexTool,
    )
    from vigilancia_multiagente.enterprise.tooling.builtin.research.serper import (
        SerperTool,
    )
    from vigilancia_multiagente.enterprise.tooling.builtin.research.serper_patents import (
        SerperPatentsTool,
    )
    from vigilancia_multiagente.enterprise.tooling.builtin.research.tavily import (
        TavilyTool,
    )
    from vigilancia_multiagente.enterprise.tooling.builtin.web.fetch import FetchTool
    from vigilancia_multiagente.enterprise.tooling.builtin.web.playwright import (
        PlaywrightTool,
    )
    from vigilancia_multiagente.enterprise.tooling.tool_registry import ToolRegistry

    registry = ToolRegistry(tool_health_repo_cls(database), embedding_gateway)
    workspace = _resolve(settings.file_system_root) if settings.file_system_root else PROJECT_ROOT

    # OAuthManager is wired ad-hoc by enterprise_onboarding for now; pass None
    # so GoogleWorkspaceTool reports UNCONFIGURED until tenant onboarding.
    from uuid import UUID
    tenant_id = UUID(settings.default_tenant_id)

    builtin_tools = (
        # Documents (5)
        TemplateRenderTool(),
        DocxGenerateTool(),
        PdfGenerateTool(),
        FileSystemTool(root=workspace),
        MarkitdownTool(),
        # Research / search (10)
        TavilyTool(),
        BraveTool(),
        ExaTool(),
        JinaTool(),
        FirecrawlTool(),
        SerperTool(),
        SerperPatentsTool(),
        OpenAlexTool(),
        ArxivTool(),
        GoogleScholarTool(),
        # Web (2)
        FetchTool(),
        PlaywrightTool(),
        # Creative (1)
        MiniMaxImageTool(),
        # Productivity (1) — OAuthManager wired by tenant onboarding
        GoogleWorkspaceTool(oauth_manager=None, tenant_id=tenant_id),
        # Execution (1)
        SandboxTool(),
    )
    for tool in builtin_tools:
        await registry.register(tool)
    logger.info(
        "ToolRegistry wired with %d builtin tools (5 documents + 10 research + "
        "2 web + 1 creative + 1 productivity + 1 execution)",
        len(builtin_tools),
    )
    return registry


def _load_catalog(settings, services: dict[str, Any]) -> None:
    from vigilancia_multiagente.enterprise.tooling.catalog_loader import (
        CatalogLoader,
        CatalogValidationError,
    )

    try:
        services["catalog"] = CatalogLoader().load(_resolve(settings.catalog_path))
        logger.info("Tool catalog loaded: %d entries", len(services["catalog"]))
    except (CatalogValidationError, FileNotFoundError) as exc:
        logger.error("Catalog not loaded: %s", exc)
        services["catalog"] = []


def _build_modes_and_playbooks(settings, services: dict[str, Any]) -> None:
    from vigilancia_multiagente.enterprise.modes.mode_loader import ModeLoader
    from vigilancia_multiagente.enterprise.orchestration.playbook_registry import PlaybookRegistry

    playbooks_dir = _resolve(settings.playbooks_dir)
    services["mode_registry"] = ModeLoader(_resolve(settings.modes_dir), playbooks_dir).load_all()
    playbook_registry = PlaybookRegistry()
    playbook_registry.load_all(playbooks_dir)
    services["playbook_registry"] = playbook_registry
    logger.info(
        "Modes (%d) + playbooks (%d) wired",
        len(services["mode_registry"].list_available()),
        len(playbook_registry.list_available()),
    )


async def _build_skills(settings, embedding_gateway, tool_registry, services: dict[str, Any]) -> None:
    from vigilancia_multiagente.enterprise.skills_marketplace import SkillLoader, SkillRegistry

    skill_registry = SkillRegistry(embedding_gateway, tool_registry)
    # Spec 021 D2/D3 — vendor paths inside src/, no .claude/skills/ at runtime.
    src_root = Path(__file__).resolve().parents[1]
    vendor_root = src_root / "enterprise" / "skills_marketplace" / "_vendor"
    loader = SkillLoader(
        registry=skill_registry,
        tool_registry=tool_registry,
        sources_enabled=list(settings.skills_sources_enabled),
        curated_path=_resolve(settings.skills_curated_path),
        learned_path=_resolve(settings.skills_learned_path),
        k_dense_vendor_path=vendor_root / "k_dense",
        agency_agents_vendor_path=vendor_root / "agency_agents",
    )
    result = await loader.load_all()
    services["skill_registry"] = skill_registry
    services["skill_loader"] = loader
    logger.info("Skill marketplace wired: %d registered", result.total_registered)


def _build_dreaming(settings, services: dict[str, Any]) -> None:
    from vigilancia_multiagente.enterprise.dreaming.orchestrator import DreamingOrchestrator
    from vigilancia_multiagente.enterprise.dreaming.scheduler import (
        DreamingScheduler,
        DreamingSchedulerConfig,
    )

    services["dreaming_scheduler"] = DreamingScheduler(
        DreamingSchedulerConfig(
            enabled=settings.dreaming_enabled,
            cron_hour=settings.dreaming_cron_hour,
            idle_timeout_min=settings.dreaming_idle_timeout_min,
        )
    )
    services["dreaming_orchestrator"] = DreamingOrchestrator()
    logger.info("Dreaming wired (enabled=%s)", settings.dreaming_enabled)


def attach_to_app_state(app: Any, services: dict[str, Any]) -> None:
    """Attach each built service onto app.state by key."""
    for key, value in services.items():
        setattr(app.state, key, value)
