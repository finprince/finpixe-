from typing import Dict, Type, List, Optional, Any
from .base import BaseSkill
from ..utils.logger import kiki_logger


class SkillRegistry:
    """
    Component — Skill Registry (Kiki 2.0)
    Central registry for worker skills. Every AI capability self-registers here.
    Supports unlimited future worker skills with zero orchestrator code changes.
    """

    _registry: Dict[str, BaseSkill] = {}

    @classmethod
    def register(cls, skill_instance: BaseSkill):
        cls._registry[skill_instance.name] = skill_instance
        kiki_logger.info(f"[SKILL REGISTRY] Registered worker skill: '{skill_instance.name}'")

    @classmethod
    def get_skill(cls, name: str) -> Optional[BaseSkill]:
        return cls._registry.get(name)

    @classmethod
    def list_skills(cls) -> List[str]:
        return list(cls._registry.keys())

    @classmethod
    def execute_skill(
        cls,
        skill_name: str,
        task_description: str,
        context_dict: Optional[Dict[str, Any]] = None,
        user_permissions: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        skill = cls.get_skill(skill_name)
        if not skill:
            kiki_logger.warning(f"[SKILL REGISTRY] Requested skill '{skill_name}' not found. Returning empty evidence.")
            return {"status": "SKILL_NOT_FOUND", "skill_name": skill_name}

        kiki_logger.info(f"[SKILL REGISTRY] Executing worker skill '{skill_name}' for task: '{task_description}'")
        try:
            res = skill.execute(task_description, context_dict=context_dict, user_permissions=user_permissions)
            res["skill_name"] = skill_name
            return res
        except Exception as err:
            kiki_logger.error(f"[SKILL REGISTRY] Error executing skill '{skill_name}': {err}")
            return {"status": "ERROR", "skill_name": skill_name, "error": str(err)}
