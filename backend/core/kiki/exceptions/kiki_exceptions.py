class KikiException(Exception):
    """Base exception for all Kiki AI ERP Agent errors."""
    pass


class SchemaException(KikiException):
    """Raised when database schema discovery or search fails."""
    pass


class QueryBuilderException(KikiException):
    """Raised when a QueryIntent cannot be validated or mapped to schema SQL."""
    pass


class SqlValidationException(KikiException):
    """Raised when an SQL query violates read-only safety rules."""
    pass


class SqlExecutionException(KikiException):
    """Raised when an SQL query execution fails or times out against MySQL."""
    pass


class OllamaException(KikiException):
    """Raised when an Ollama LLM HTTP request or output parsing fails."""
    pass


class InvestigationException(KikiException):
    """Raised when the investigation workflow fails or reaches max steps without evidence."""
    pass
