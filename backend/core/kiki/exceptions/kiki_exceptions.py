"""
KIKI 2027 Exception Suite
=========================
Custom exceptions for tenant security, model runtime timeouts, and SQL validation guards.
"""

class KikiBaseException(Exception):
    """Base exception for all KIKI AI Operating System errors."""
    def __init__(self, message: str, code: str = "KIKI_ERROR", details: dict = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}


class KikiTenantSecurityException(KikiBaseException):
    """Raised when tenant scoping is missing or security validation fails."""
    def __init__(self, message: str = "Tenant security boundary violation.", details: dict = None):
        super().__init__(message=message, code="TENANT_SECURITY_VIOLATION", details=details)


class KikiRBACPermissionException(KikiBaseException):
    """Raised when a user attempts an operation exceeding their RBAC permissions."""
    def __init__(self, message: str = "User permission denied for requested capability.", details: dict = None):
        super().__init__(message=message, code="RBAC_PERMISSION_DENIED", details=details)


class KikiModelTimeoutException(KikiBaseException):
    """Raised when local Ollama model inference times out."""
    def __init__(self, message: str = "Local AI model execution timed out.", details: dict = None):
        super().__init__(message=message, code="MODEL_TIMEOUT", details=details)


class KikiSQLValidationException(KikiBaseException):
    """Raised when compiled SQL fails pre-execution safety or tenant checks."""
    def __init__(self, message: str = "Compiled SQL failed security validation.", details: dict = None):
        super().__init__(message=message, code="SQL_VALIDATION_FAILED", details=details)


class KikiQueryCostExceededException(KikiBaseException):
    """Raised when query cost guard predicts excessive row scans."""
    def __init__(self, message: str = "Query cost exceeded maximum safety threshold.", details: dict = None):
        super().__init__(message=message, code="QUERY_COST_EXCEEDED", details=details)
