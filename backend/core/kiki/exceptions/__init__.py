"""
Standardized exceptions package for Kiki AI ERP Agent.
"""
from .kiki_exceptions import (
    KikiException,
    SchemaException,
    QueryBuilderException,
    SqlValidationException,
    SqlExecutionException,
    OllamaException,
    InvestigationException,
)

__all__ = [
    "KikiException",
    "SchemaException",
    "QueryBuilderException",
    "SqlValidationException",
    "SqlExecutionException",
    "OllamaException",
    "InvestigationException",
]
