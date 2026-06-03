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

    # ── Audit log (Spec 021 F5a.D / T136) — single JSONL writer
    #    threaded through the runtime entry points (tools/LLM/complexity/
    #    subagents). Optional in tests; in production a default AuditLog
    #    writes to ~/.vigilador/audit/events_<date>.jsonl.
    from vigilancia_multiagente.enterprise.governance.audit_log import AuditLog
    audit_log = AuditLog()
    services["audit_log"] = audit_log

    # ── ToolRegistry + builtin tools + catalog metadata (specs 009/018) ──
    tool_registry = await _build_tool_registry(
        settings, database, embedding_gateway, ToolHealthRepository, audit_log,
    )
    services["tool_registry"] = tool_registry
    _load_catalog(settings, services)

    # ── Modes + Playbooks (spec 011/012) ──
    _build_modes_and_playbooks(settings, services)

    # ── Skill marketplace (spec 015) ──
    if settings.skills_marketplace_enabled and tool_registry is not None:
        await _build_skills(settings, embedding_gateway, tool_registry, services)

    # ── Dreaming (spec 017) — scheduler + orchestrator, default disabled ──
    _build_dreaming(settings, services)

    # ── Dispatcher (spec 021 F4a.H / T121) — composition root for the
    #    end-to-end request flow. Optional: only wired when ModeRegistry
    #    is present (set by _build_modes_and_playbooks).
    _build_dispatcher(settings, services)

    return services


async def _build_tool_registry(settings, database, embedding_gateway, tool_health_repo_cls, audit_log=None):
    # Documents tools (spec 009 + spec 018 — already shipped)
    # Spec 021 D5 native-first WRAP-SDK + CLONE-UPSTREAM tools (T015-T031).
    from vigilancia_multiagente.infra.embeddings.embedding_cache import EmbeddingCache
    from vigilancia_multiagente.enterprise.tooling.builtin.creative.minimax_image import (
        MiniMaxImageTool,
    )
    from vigilancia_multiagente.enterprise.tooling.builtin.desktop.computer_use import (
        ComputerUseTool,
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

    # FR-001: Two-tier embedding cache for tool descriptions
    cache_dir = PROJECT_ROOT / ".vigilador" / "cache" / "embeddings"
    embedding_cache = EmbeddingCache(cache_dir=cache_dir, filename="tools.json")
    embedding_cache.load_from_disk()

    registry = ToolRegistry(
        tool_health_repo_cls(database), 
        embedding_gateway, 
        audit_log=audit_log,
        embedding_cache=embedding_cache,
    )
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
        # Desktop (1) — opt-in via settings.computer_use_enabled / VT_COMPUTER_USE_ENABLED
        ComputerUseTool(
            enabled=settings.computer_use_enabled,
            app_allowlist=tuple(settings.computer_use_app_allowlist),
        ),
    )
    for tool in builtin_tools:
        await registry.register(tool)
    
    # Flush tool embeddings to disk after registration
    if embedding_cache:
        embedding_cache.flush_to_disk()
        
    logger.info(
        "ToolRegistry wired with %d builtin tools (5 documents + 10 research + "
        "2 web + 1 creative + 1 productivity + 1 execution + 1 desktop)",
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
    from vigilancia_multiagente.enterprise.modes.mode_resolver import ModeResolver
    from vigilancia_multiagente.enterprise.orchestration.playbook_registry import PlaybookRegistry

    playbooks_dir = _resolve(settings.playbooks_dir)
    services["mode_registry"] = ModeLoader(_resolve(settings.modes_dir), playbooks_dir).load_all()
    services["mode_resolver"] = ModeResolver(services["mode_registry"])
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
    from vigilancia_multiagente.enterprise.skills_marketplace.skill_catalog import (
        SkillCatalog,
        SkillCatalogError,
    )
    from vigilancia_multiagente.infra.embeddings.embedding_cache import EmbeddingCache

    # FR-003: Create EmbeddingCache for skill embeddings
    embedding_cache = EmbeddingCache()
    embedding_cache.load_from_disk()

    skill_registry = SkillRegistry(embedding_gateway, tool_registry, embedding_cache=embedding_cache)
    # Spec 021 D2/D3 — vendor paths inside src/, no .claude/skills/ at runtime.
    src_root = Path(__file__).resolve().parents[1]
    vendor_root = src_root / "enterprise" / "skills_marketplace" / "_vendor"

    # Centralized taxonomy + overrides (Spec 021 organization layer).
    catalog: SkillCatalog | None = None
    taxonomy_path = PROJECT_ROOT / "config" / "skills" / "taxonomy.yaml"
    catalog_path = PROJECT_ROOT / "config" / "skills" / "catalog.yaml"
    if taxonomy_path.is_file():
        try:
            catalog = SkillCatalog(
                taxonomy_path=taxonomy_path,
                catalog_path=catalog_path if catalog_path.is_file() else None,
            )
            logger.info(
                "SkillCatalog loaded: %d categories, %d aliases, %d disabled",
                len(catalog.categories()),
                len(catalog.aliases()),
                len(catalog.disabled()),
            )
        except SkillCatalogError as exc:
            logger.error(
                "SkillCatalog disabled — taxonomy/catalog YAML invalid: %s", exc
            )
            catalog = None
    else:
        logger.warning(
            "SkillCatalog not wired — taxonomy.yaml not found at %s",
            taxonomy_path,
        )

    loader = SkillLoader(
        registry=skill_registry,
        tool_registry=tool_registry,
        sources_enabled=list(settings.skills_sources_enabled),
        curated_path=_resolve(settings.skills_curated_path),
        learned_path=_resolve(settings.skills_learned_path),
        k_dense_vendor_path=vendor_root / "k_dense",
        agency_agents_vendor_path=vendor_root / "agency_agents",
        catalog=catalog,
        embedding_cache=embedding_cache,
        cold_skills_enabled=settings.cold_skills_enabled,
    )
    result = await loader.load_all()
    services["skill_registry"] = skill_registry
    services["skill_loader"] = loader
    services["skill_catalog"] = catalog
    logger.info(
        "Skill marketplace wired: %d registered, %d filtered by catalog",
        result.total_registered, result.total_skipped_by_catalog,
    )


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


def _build_dispatcher(settings: Any, services: dict[str, Any]) -> None:
    """Spec 021 F4a.H — wire the end-to-end Dispatcher.

    Skips silently if the prerequisites (mode_registry / mode_resolver) are
    missing. The HTTP route falls back to a 503 with a clear message in
    that case (constitución #4 explicit error).
    """
    mode_registry = services.get("mode_registry")
    mode_resolver = services.get("mode_resolver")
    if mode_registry is None or mode_resolver is None:
        logger.info(
            "Dispatcher: skipped (mode_registry=%s mode_resolver=%s)",
            bool(mode_registry), bool(mode_resolver),
        )
        return

    from vigilancia_multiagente.enterprise.modes.mode_resolver_cascade import (
        CascadeResolver,
    )
    from vigilancia_multiagente.enterprise.orchestration.dispatcher import (
        Dispatcher,
        DispatcherDeps,
    )

    cascade = CascadeResolver(
        registry=mode_registry,
        channels_dir=PROJECT_ROOT / "config" / "channels",
        classifier=None,  # F4b will plug in an LLM-driven mode classifier
        default_mode="default",
    )

    # Optional: wire the technology-watch executor when BranchCoordinator
    # is reachable. The executor wraps the 2.0 coordinator without touching it.
    executor_by_playbook: dict[str, Any] = {}
    branch_coordinator = services.get("branch_coordinator")
    if branch_coordinator is not None:
        try:
            import importlib.util as _ilu
            import sys as _sys

            wrapper_path = (
                PROJECT_ROOT / "plugins" / "technology-watch"
                / "coordinator_wrapper.py"
            )
            if wrapper_path.is_file():
                spec = _ilu.spec_from_file_location(
                    "_tw_wrapper", wrapper_path
                )
                if spec is not None and spec.loader is not None:
                    mod = _ilu.module_from_spec(spec)
                    _sys.modules.setdefault("_tw_wrapper", mod)
                    spec.loader.exec_module(mod)
                    executor_by_playbook["technology-watch"] = (
                        mod.TechnologyWatchExecutor(coordinator=branch_coordinator)
                    )
        except Exception as exc:
            logger.warning(
                "Dispatcher: technology-watch executor wiring failed: %s", exc
            )

    deps = DispatcherDeps(
        cascade_resolver=cascade,
        mode_resolver=mode_resolver,
        complexity_classifier=None,  # F4b plugs in the real classifier
        playbook_dir=PROJECT_ROOT / "config" / "playbooks",
        executor_by_playbook=executor_by_playbook,
    )
    dispatcher = Dispatcher(deps=deps)
    services["dispatcher"] = dispatcher
    logger.info(
        "Dispatcher wired (executors registered: %d)",
        len(executor_by_playbook),
    )
