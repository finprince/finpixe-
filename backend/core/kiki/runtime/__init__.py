"""
Runtime package for Kiki AI ERP Agent.
Contains OllamaRuntime (LLM Client) and InvestigationEngine (Workflow Orchestrator).
"""
from .ollama_runtime import OllamaRuntime
from .investigation_engine import InvestigationEngine

__all__ = ["OllamaRuntime", "InvestigationEngine"]
