"""Skill Marketplace — public API.

Spec 021 D2/D3: ``ClaudeLocalAdapter`` is no longer wired into runtime;
the file remains as reference only. Public adapters are
``KDenseAdapter`` and ``AgencyAgentsAdapter``.
"""

from vigilancia_multiagente.enterprise.skills_marketplace.agency_agents_adapter import (
    AgencyAgentsAdapter,
)
from vigilancia_multiagente.enterprise.skills_marketplace.k_dense_adapter import (
    KDenseAdapter,
)
from vigilancia_multiagente.enterprise.skills_marketplace.skill_loader import SkillLoader
from vigilancia_multiagente.enterprise.skills_marketplace.skill_models import (
    CommandSkill,
    SkillBody,
    SkillCard,
    SkillSource,
    SkillState,
    SkillSummary,
)
from vigilancia_multiagente.enterprise.skills_marketplace.skill_registry import SkillRegistry

__all__ = [
    "AgencyAgentsAdapter",
    "CommandSkill",
    "KDenseAdapter",
    "SkillBody",
    "SkillCard",
    "SkillLoader",
    "SkillRegistry",
    "SkillSource",
    "SkillState",
    "SkillSummary",
]
