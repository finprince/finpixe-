"""
Structured JSON Logger for KIKI 2027
====================================
Formats log records as structured JSON including trace_id, tenant_id, and user_id.
"""
import logging
import json
import time

class KikiStructuredLogger(logging.LoggerAdapter):
    """Logger adapter injecting KIKI contextual metadata into JSON logs."""
    
    def __init__(self, logger: logging.Logger, extra: dict = None):
        super().__init__(logger, extra or {})

    def process(self, msg: str, kwargs: dict) -> tuple:
        extra = self.extra.copy()
        if "extra" in kwargs:
            extra.update(kwargs["extra"])
            del kwargs["extra"]
            
        log_payload = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "message": msg,
            "trace_id": extra.get("trace_id", "N/A"),
            "tenant_id": extra.get("tenant_id", "GLOBAL"),
            "user_id": extra.get("user_id", "SYSTEM"),
            "component": extra.get("component", "KIKI_CORE")
        }
        
        return json.dumps(log_payload), kwargs

def get_kiki_logger(name: str = "kiki", trace_id: str = None, tenant_id: str = None, user_id: str = None) -> KikiStructuredLogger:
    raw_logger = logging.getLogger(f"kiki.{name}")
    if not raw_logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        raw_logger.addHandler(handler)
        raw_logger.setLevel(logging.INFO)
        
    return KikiStructuredLogger(raw_logger, {
        "trace_id": trace_id,
        "tenant_id": tenant_id,
        "user_id": user_id,
        "component": name
    })
