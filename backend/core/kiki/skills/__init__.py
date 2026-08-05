from .base import BaseSkill
from .registry import SkillRegistry
from .navigation_skill import NavigationSkill
from .investigation_skill import InvestigationSkill
from .kpi_skill import KPISkill
from .gst_skill import GSTSkill
from .ocr_skill import OCRSkill
from .help_skill import HelpSkill
from .workflow_skill import WorkflowSkill
from .action_skill import ActionSkill
from .reporting_skill import ReportingSkill
from .analytics_skill import AnalyticsSkill

# Auto-register all worker skills into SkillRegistry
for skill_cls in [
    NavigationSkill,
    InvestigationSkill,
    KPISkill,
    GSTSkill,
    OCRSkill,
    HelpSkill,
    WorkflowSkill,
    ActionSkill,
    ReportingSkill,
    AnalyticsSkill,
]:
    SkillRegistry.register(skill_cls())

__all__ = [
    "BaseSkill",
    "SkillRegistry",
    "NavigationSkill",
    "InvestigationSkill",
    "KPISkill",
    "GSTSkill",
    "OCRSkill",
    "HelpSkill",
    "WorkflowSkill",
    "ActionSkill",
    "ReportingSkill",
    "AnalyticsSkill",
]
