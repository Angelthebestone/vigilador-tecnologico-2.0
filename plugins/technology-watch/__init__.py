"""Technology-watch plugin — wraps the 2.0 BranchCoordinator.

Spec 021 F4a.D / T107. Conserves the 2.0 flow (BranchCoordinator + 6
branch agents) verbatim — no reimplementation. The plugin exposes the
``AgentExecutor`` Protocol expected by ``PlaybookRunner`` so the
``technology-watch`` playbook can route through it.

Constitución #5 cambios quirúrgicos: ``application/execution/branch_coordinator.py``
is NOT modified by this plugin. Verified by ``git diff --stat``.
"""

from .coordinator_wrapper import TechnologyWatchExecutor

__all__ = ["TechnologyWatchExecutor"]
