"""
KIKI Dependency Injection Container
===================================
Simple, thread-safe DI container for registration and resolution of provider singletons.
"""
from typing import Dict, Type, Any

class DIContainer:
    _registry: Dict[str, Any] = {}
    _singletons: Dict[str, Any] = {}

    @classmethod
    def register(cls, interface_key: str, implementation_class: Type, singleton: bool = True) -> None:
        """Register an implementation for an interface key."""
        cls._registry[interface_key] = {
            "class": implementation_class,
            "singleton": singleton
        }

    @classmethod
    def resolve(cls, interface_key: str) -> Any:
        """Resolve an instance for the requested interface key."""
        if interface_key not in cls._registry:
            raise KeyError(f"No provider registered in DIContainer for key: '{interface_key}'")

        spec = cls._registry[interface_key]
        if spec["singleton"]:
            if interface_key not in cls._singletons:
                cls._singletons[interface_key] = spec["class"]()
            return cls._singletons[interface_key]
        
        return spec["class"]()

    @classmethod
    def clear(cls) -> None:
        """Clear all registered singletons (primarily for unit testing)."""
        cls._registry.clear()
        cls._singletons.clear()
