from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class BaseSkill(ABC):
    """
    Abstract Base Class for Kiki 2.0 Worker Skills.
    Worker skills are stateless implementation tools.
    Responsibilities: Receive task -> Execute task -> Return raw evidence.
    """

    name: str = "BaseSkill"
    description: str = "Abstract base worker skill"

    @abstractmethod
    def execute(
        self,
        task_description: str,
        context_dict: Optional[Dict[str, Any]] = None,
        user_permissions: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        pass
