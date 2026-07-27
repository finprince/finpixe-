import json
import re
import time
from typing import Any, Dict

try:
    import json_repair
except ImportError:
    json_repair = None


def repair_and_parse_json(text: str) -> Any:
    """
    Parses JSON string from LLM output. Uses json_repair if available,
    or regex block extraction fallback.
    """
    if not text or not isinstance(text, str):
        raise ValueError("Input to repair_and_parse_json must be a non-empty string.")

    cleaned = text.strip()
    # Remove markdown code block fences if present
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned).strip()

    # Try standard json.loads first
    try:
        return json.loads(cleaned)
    except Exception:
        pass

    # Try json_repair if installed
    if json_repair:
        try:
            repaired = json_repair.repair_json(cleaned)
            return json.loads(repaired)
        except Exception:
            pass

    # Regex extraction of outermost array or object
    obj_match = re.search(r"(\{.*\}|\[.*\])", cleaned, re.DOTALL)
    if obj_match:
        try:
            return json.loads(obj_match.group(1))
        except Exception:
            pass

    raise ValueError(f"Unable to parse valid JSON from content: {text[:100]}...")


def clean_text(text: str) -> str:
    """Removes extra whitespace and cleans input text."""
    if not text:
        return ""
    return " ".join(text.strip().split())


class Timer:
    """Simple context manager to measure execution time in milliseconds."""
    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, *args):
        self.end = time.perf_counter()
        self.interval_ms = (self.end - self.start) * 1000.0
