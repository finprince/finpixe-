"""
core/ai_proxy.py — AI Extraction Proxy
========================================
Provider: Qwen-VL (self-hosted, OpenAI-compatible API)
Former provider: Google Gemini (removed)

All Google GenAI SDK dependencies have been eliminated.
The provider abstraction layer (core/providers/) is the sole AI interface.

Configuration:
    QWEN_MODEL    = qwen-vl-max          (model name served by your vLLM server)
    QWEN_API_BASE = http://localhost:8080/v1  (your Qwen server base URL)
    QWEN_API_KEY  = EMPTY                (leave empty for unauthenticated local servers)
"""

import os
import json
import re
import base64
import time
import hashlib
import logging
import threading
import random
from typing import Dict, Any, Optional, Tuple, List
from django.db import models
from django.core.cache import cache
from django.conf import settings
from dotenv import load_dotenv

# Ensure environment variables are loaded
load_dotenv(override=False)

# ── PROVIDER CONFIGURATION ──
AI_MODEL_NAME = os.getenv("MISTRAL_OCR_MODEL", "mistral-ocr-latest")

logger = logging.getLogger(__name__)

# ── PROVIDER SINGLETON ──
# Instantiated once at module load. All workers share this instance.
from core.providers.mistral_structured_provider import MistralStructuredProvider
_ai_provider = MistralStructuredProvider()


# ═══════════════════════════════════════════════════════════════════════════════
# JSON UTILITIES (provider-agnostic, unchanged from former Gemini version)
# ═══════════════════════════════════════════════════════════════════════════════

def safe_extract_json(text: str) -> Optional[str]:
    """
    Production-grade JSON extractor.
    - Handles ```json ... ``` blocks
    - Handles ``` ... ``` blocks
    - Handles plain JSON text
    - Locates boundaries by brace counting
    - Sanitizes control characters
    """
    if not text:
        return None

    # Remove potentially dangerous control characters except common whitespace
    text = "".join(ch for ch in text if ch >= " " or ch in "\n\r\t")

    clean_text = text.strip()

    # 1. Standard markdown extract
    if "```json" in clean_text:
        try:
            clean_text = clean_text.split("```json")[1].split("```")[0].strip()
        except IndexError:
            pass
    elif "```" in clean_text:
        try:
            clean_text = clean_text.split("```")[1].split("```")[0].strip()
        except IndexError:
            pass

    # 2. Brace-based boundary detection
    if not (clean_text.startswith('{') and (clean_text.endswith('}') or clean_text.endswith(']'))):
        start = clean_text.find('{')
        if start == -1:
            start = clean_text.find('[')

        if start != -1:
            brace_count = 0
            bracket_count = 0
            for i in range(start, len(clean_text)):
                char = clean_text[i]
                if char == '{': brace_count += 1
                elif char == '}': brace_count -= 1
                elif char == '[': bracket_count += 1
                elif char == ']': bracket_count -= 1

                if brace_count == 0 and bracket_count == 0:
                    return clean_text[start:i+1].strip()

    return clean_text if (clean_text.startswith('{') or clean_text.startswith('[')) else None


def repair_json(text: str) -> str:
    """
    Emergency JSON repair layer for common LLM hallucinations.
    Handles trailing commas and missing braces.
    """
    if not text: return ""
    repaired = text.replace('\u201c', '"').replace('\u201d', '"').replace('\u2018', "'").replace('\u2019', "'")
    repaired = re.sub(r",\s*([\]}])", r"\1", repaired)
    brace_diff = repaired.count('{') - repaired.count('}')
    if brace_diff > 0: repaired += ('}' * brace_diff)
    bracket_diff = repaired.count('[') - repaired.count(']')
    if bracket_diff > 0: repaired += (']' * bracket_diff)
    return repaired


# ═══════════════════════════════════════════════════════════════════════════════
# API KEY MANAGER (supports QWEN_API_KEY with comma-separated rotation)
# ═══════════════════════════════════════════════════════════════════════════════

class APIKeyManager:
    """
    Rotates through multiple Qwen API keys and tracks health.
    For self-hosted servers without authentication, a single placeholder key is used.
    """

    def __init__(self):
        self.api_keys = []
        self.unhealthy_keys = set()
        self.rotation_counter = 0
        self.recheck_interval = 600  # 10 minutes quarantine before re-testing
        self._sync_keys()

    def _sync_keys(self):
        raw_keys = os.getenv('MISTRAL_API_KEY')
        if not raw_keys:
            self.api_keys = []
            return
        self.api_keys = [k.strip() for k in raw_keys.split(',') if k.strip()]
        if not self.api_keys:
            self.api_keys = ['EMPTY']

    def get_healthy_key(self) -> Optional[str]:
        self._sync_keys()
        if not self.api_keys: return 'EMPTY'
        healthy_keys = [k for k in self.api_keys if k not in self.unhealthy_keys]
        keys_to_use = healthy_keys if healthy_keys else self.api_keys
        if healthy_keys:
            self.rotation_counter += 1
            return healthy_keys[self.rotation_counter % len(healthy_keys)]
        return keys_to_use[0] if keys_to_use else 'EMPTY'

    def mark_key_unhealthy(self, api_key: str):
        if api_key == 'EMPTY':
            return  # Never quarantine the placeholder key
        self.unhealthy_keys.add(api_key)
        threading.Timer(
            self.recheck_interval,
            lambda: self._recheck_key(api_key)
        ).start()

    def _recheck_key(self, api_key: str):
        try:
            healthy = _ai_provider.recheck_key_health(api_key, AI_MODEL_NAME)
            if healthy:
                self.unhealthy_keys.discard(api_key)
                logger.info(f"[KEY_RECHECK_PASS] Key ...{api_key[-6:]} is healthy again.")
        except Exception as e:
            logger.warning(f"[KEY_RECHECK_FAIL] Key ...{api_key[-6:]} still unhealthy: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# CIRCUIT BREAKER (provider-agnostic, unchanged)
# ═══════════════════════════════════════════════════════════════════════════════

class CircuitBreaker:
    def __init__(self):
        self.failure_threshold = 5
        self.reset_timeout = 300
        self.failures = 0
        self.last_failure = 0

    def is_open(self) -> bool:
        now = time.time()
        if self.failures >= self.failure_threshold:
            if now - self.last_failure < self.reset_timeout: return True
            self.failures = 0
        return False

    def record_failure(self):
        self.failures += 1
        self.last_failure = time.time()

    def record_success(self):
        if self.failures > 0: self.failures -= 1


# ═══════════════════════════════════════════════════════════════════════════════
# RATE LIMITER (provider-agnostic, unchanged)
# ═══════════════════════════════════════════════════════════════════════════════

class RateLimiter:
    def _get_redis(self):
        from core.redis_orchestrator import orchestrator
        if not orchestrator.redis:
            orchestrator._connect()
        return orchestrator.redis

    def check_rate_limit(self, key: str, limit: int = None, window: float = 1.0) -> Dict[str, Any]:
        r = self._get_redis()
        if not r:
            return {'allowed': True, 'retry_after': 0}

        if limit is None:
            limit = int(os.getenv('AI_MAX_RPS', '10'))

        now = time.time()
        clear_before = now - window

        try:
            pipe = r.pipeline()
            pipe.zremrangebyscore(key, 0, clear_before)
            pipe.zcard(key)
            pipe.zadd(key, {str(now): now})
            pipe.expire(key, int(window * 2) or 1)

            res = pipe.execute()
            count = res[1]

            if count >= limit:
                r.zrem(key, str(now))
                retry_after = max(0.1, window - (now - clear_before))
                return {'allowed': False, 'retry_after': retry_after}

            return {'allowed': True, 'retry_after': 0}
        except Exception as e:
            logger.error(f"[RATE_LIMIT_ERROR] {e}")
            return {'allowed': True, 'retry_after': 0}


# ═══════════════════════════════════════════════════════════════════════════════
# DISTRIBUTED CONCURRENCY MANAGER (provider-agnostic, unchanged)
# ═══════════════════════════════════════════════════════════════════════════════

class DistributedConcurrencyManager:
    """
    Redis-backed atomic semaphore for distributed concurrency governance.
    Replaces brittle DB locks with auto-expiring lease tokens to prevent permit leaks.
    """
    def __init__(self, max_concurrent=20):
        self.global_max = max_concurrent
        self.acquire_script = """
        local global_key = KEYS[1]
        local tenant_key = KEYS[2]
        local permit_id = ARGV[1]
        local current_time = tonumber(ARGV[2])
        local expiration_time = tonumber(ARGV[3])
        local global_limit = tonumber(ARGV[4])
        local tenant_limit = tonumber(ARGV[5])

        -- Cleanup expired
        redis.call('ZREMRANGEBYSCORE', global_key, 0, current_time)
        if tenant_key ~= "" then
            redis.call('ZREMRANGEBYSCORE', tenant_key, 0, current_time)
        end

        -- Check limits
        local global_count = redis.call('ZCARD', global_key)
        if global_count >= global_limit then
            return 0
        end

        if tenant_key ~= "" then
            local tenant_count = redis.call('ZCARD', tenant_key)
            if tenant_count >= tenant_limit then
                return 0
            end
        end

        -- Acquire
        redis.call('ZADD', global_key, expiration_time, permit_id)
        if tenant_key ~= "" then
            redis.call('ZADD', tenant_key, expiration_time, permit_id)
        end

        return 1
        """
        self._lua_sha = None

    def _get_redis(self):
        from core.redis_orchestrator import orchestrator
        if not orchestrator.redis:
            orchestrator._connect()
        return orchestrator.redis

    def acquire_permit(self, permit_id: str, tenant_id: str = "global") -> bool:
        r = self._get_redis()
        if not r:
            logger.warning("[REDIS_UNAVAILABLE] Concurrency governor falling back to deny-all.")
            return False

        from core.sqs import queue_service
        try:
            q_depth = queue_service.get_queue_depth('ai')
        except Exception:
            q_depth = 0

        effective_max = self.global_max
        if os.getenv('CLUSTER_ENV', 'local') == 'local':
            effective_max = max(effective_max, 20)
        elif q_depth > 2000:
            effective_max = max(5, self.global_max // 4)
            logger.warning(f"[OVERLOAD_THROTTLE] Q_DEPTH={q_depth}. Reducing concurrency to {effective_max}")
        elif q_depth > 1000:
            effective_max = max(10, self.global_max // 2)

        global_key = "ai_concurrency:global"
        tenant_key = f"ai_concurrency:tenant:{tenant_id}" if tenant_id and tenant_id != "global" else ""

        now = time.time()
        expiration = now + 900  # 15-minute max lease to match watchdog
        tenant_limit = 20 if os.getenv('CLUSTER_ENV', 'local') == 'local' else 15

        try:
            if not self._lua_sha:
                self._lua_sha = r.script_load(self.acquire_script)

            keys = [global_key, tenant_key]
            args = [permit_id, now, expiration, effective_max, tenant_limit]

            result = r.evalsha(self._lua_sha, len(keys), *keys, *args)
            return result == 1 or result in (b'OK', 'OK', True, 1)
        except Exception as e:
            logger.error(f"[QUOTA_ACQUIRE_ERROR] {e}")
            return False

    def release_permit(self, permit_id: str, tenant_id: str = "global"):
        r = self._get_redis()
        if not r:
            return

        global_key = "ai_concurrency:global"
        tenant_key = f"ai_concurrency:tenant:{tenant_id}" if tenant_id and tenant_id != "global" else ""

        try:
            r.zrem(global_key, permit_id)
            if tenant_key:
                r.zrem(tenant_key, permit_id)
        except Exception as e:
            logger.error(f"[QUOTA_RELEASE_ERROR] {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCES
# ═══════════════════════════════════════════════════════════════════════════════

api_key_manager = APIKeyManager()
circuit_breaker = CircuitBreaker()
rate_limiter = RateLimiter()
concurrency_governor = DistributedConcurrencyManager(
    max_concurrent=int(os.getenv('AI_GLOBAL_CONCURRENCY', '10'))
)


# ═══════════════════════════════════════════════════════════════════════════════
# STARTUP VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════






def validate_ai_on_startup() -> bool:
    """
    Called at Django startup / worker startup to verify Mistral API key configuration and endpoint.
    Refuses provider initialization if required Mistral config is missing or the endpoint is invalid.
    """
    api_key = os.getenv('MISTRAL_API_KEY')
    if not api_key:
        logger.error("[AI_PROVIDER_STARTUP_FAILURE] MISTRAL_API_KEY environment variable is missing.")
        _ai_provider.mark_invalid("MISSING_CONFIG", "MISTRAL_API_KEY environment variable is missing.")
        return False

    api_key_manager._sync_keys()

    model_name = _ai_provider.get_model_name()
    health = _ai_provider.recheck_key_health(api_key, model_name)

    health_log = (
        f"[AI_PROVIDER_HEALTHCHECK]\n"
        f"provider=Mistral\n"
        f"model={model_name}\n"
        f"result={'SUCCESS' if health else 'FAILED'}"
    )
    logger.info(health_log)
    print(health_log)

    if not health:
        logger.error(
            f"[MISTRAL_API_INVALID] API key check failed. Key is invalid or unreachable."
        )
        logger.error(
            f"[AI_PROVIDER_STARTUP_FAILURE] reason=Endpoint health check failed."
        )
        _ai_provider.mark_invalid("API_UNREACHABLE", "Mistral API health check failed.")
        return False

    logger.info(
        f"[AI_PROVIDER_READY] provider=Mistral model={model_name} "
        f"keys={len(api_key_manager.api_keys)}"
    )
    _ai_provider.mark_valid()
    return True



# ═══════════════════════════════════════════════════════════════════════════════
# ERROR TYPES
# ═══════════════════════════════════════════════════════════════════════════════

class TerminalTaskError(Exception):
    """Raised for non-retryable AI orchestration errors."""
    pass


class ProviderSaturatedError(Exception):
    """Raised when the AI provider or local concurrency limits are saturated."""
    pass


# ═══════════════════════════════════════════════════════════════════════════════
# ERROR CLASSIFICATION
# ═══════════════════════════════════════════════════════════════════════════════

def is_retryable_ai_error(e: Exception) -> bool:
    """
    Implements global retry classification.
    Non-retryable errors abort immediately; retryable errors trigger backoff.
    """
    err_str = str(e).lower()
    # Non-retryable
    if any(k in err_str for k in [
        "400", "401", "403", "404", "model not found",
        "invalid api key", "api key not valid", "malformed",
        "invalid_argument", "permission_denied", "unauthenticated",
        "quota_disabled", "billing not enabled", "invalid_ai_endpoint"
    ]):
        return False
    # Retryable
    if any(k in err_str for k in [
        "429", "500", "502", "503", "timeout", "connection reset",
        "capacity", "too many requests"
    ]):
        return True
    return True  # Default: treat as transient


# ═══════════════════════════════════════════════════════════════════════════════
# CORE EXECUTION WITH RETRY
# ═══════════════════════════════════════════════════════════════════════════════

def execute_with_retry(prompt: Any, request_data: dict, api_key: str) -> str:
    """
    Production-grade retry logic with exponential backoff and jitter.
    Delegates to QwenProvider.call_single() for each attempt.

    STRICT RETRY RULE:
    - Do NOT retry: auth failures, invalid keys, malformed requests.
    - Retry ONLY: transient network failures, rate limits, 5xx provider failures.
    """
    import random
    from core.observability import observability

    MAX_ATTEMPTS = 5
    base_delay = 1

    tenant_id = request_data.get('tenant_id') or (request_data.get('metadata') or {}).get('tenant_id')
    record_id = request_data.get('record_id') or (request_data.get('metadata') or {}).get('record_id')
    page_number = request_data.get('page_number') or request_data.get('page_index')

    current_model = AI_MODEL_NAME
    last_error = None
    attempt = 0

    logger.info(
        f"[AI_MODEL_SELECTED] provider=Mistral model={current_model} "
        f"tenant_id={tenant_id} record_id={record_id} page_number={page_number}"
    )

    # ── RESOLVE PROMPT PARTS ──
    if isinstance(prompt, list):
        # Former Gemini multipart list format — extract text and image
        prompt_text = ""
        image_b64 = None
        mime_type = "image/jpeg"
        batch_images = None

        for part in prompt:
            if isinstance(part, str):
                prompt_text = part
            elif isinstance(part, dict) and "inline_data" in part:
                # Former Gemini inline_data format → convert to b64 string
                raw_bytes = part["inline_data"].get("data", b"")
                if isinstance(raw_bytes, bytes):
                    image_b64 = base64.b64encode(raw_bytes).decode("utf-8")
                else:
                    image_b64 = raw_bytes  # already b64 string
                mime_type = part["inline_data"].get("mime_type", "image/jpeg")
    else:
        # Plain string prompt (text-only or already preprocessed)
        prompt_text = prompt if isinstance(prompt, str) else str(prompt)
        image_b64 = None
        mime_type = "image/jpeg"
        batch_images = None

    # Handle batch_images from request_data directly
    if request_data.get("batch_images"):
        batch_images = request_data["batch_images"]
        image_b64 = None  # batch mode overrides single-image mode
    elif request_data.get("image_data"):
        image_b64 = request_data["image_data"]
        mime_type = request_data.get("mime_type", "image/jpeg")
        batch_images = None
        # prompt_text was already set above from prompt list or string
        if not prompt_text:
            prompt_text = request_data.get("prompt", "Extract data")

    while attempt < MAX_ATTEMPTS:
        try:
            result = _ai_provider.call_single(
                prompt_text=prompt_text,
                image_b64=image_b64,
                mime_type=mime_type,
                batch_images=batch_images,
                request_data=request_data,
                api_key=api_key,
                model_name=current_model,
                attempt_label=f"Attempt {attempt + 1}",
            )
            return result
        except TerminalTaskError as e:
            logger.error(
                f"[AI_TERMINAL_FAILURE] provider=Mistral model={current_model} "
                f"tenant_id={tenant_id} record_id={record_id} page_number={page_number} "
                f"error={str(e)[:100]}"
            )
            raise
        except Exception as e:
            last_error = e
            retryable = is_retryable_ai_error(e)

            logger.info(
                f"[AI_ERROR_CLASSIFIED] provider=Mistral model={current_model} "
                f"tenant_id={tenant_id} record_id={record_id} page_number={page_number} "
                f"retryable={retryable} error={str(e)[:100]}"
            )

            if not retryable:
                logger.error(
                    f"[AI_TERMINAL_FAILURE] provider=Mistral model={current_model} "
                    f"error={str(e)[:100]}"
                )
                raise TerminalTaskError(str(e))

            if attempt < MAX_ATTEMPTS - 1:
                delay = (base_delay * (2 ** attempt)) + (random.random() * 0.5)
                logger.warning(
                    f"[AI_RETRY] Mistral/{current_model} Attempt {attempt+1} failed: {e}. "
                    f"Retrying in {delay:.2f}s..."
                )
                observability.ai_metric(event="AI_RETRY", attempt=attempt + 1, error=str(e)[:100])
                time.sleep(delay)
                attempt += 1
            else:
                logger.error(f"[AI_EXHAUSTED] All {MAX_ATTEMPTS} attempts failed on {current_model}: {e}")
                observability.ai_metric(event="AI_EXHAUSTED", error=str(e)[:100])
                raise e

    raise last_error


# [SHADOW_MODE_REMOVED] Legacy shadow mode and bypass validation functions deleted.


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN PROCESS ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def process_ai_request(request_data: dict) -> dict:
    """
    Central AI extraction dispatcher.
    Called by AIWorker and synchronous extraction paths.

    Governs:
      - Tenant context validation
      - Overload shedding
      - Distributed concurrency (Redis semaphore)
      - RPS rate limiting (Redis sorted-set)
      - Mock mode bypass
      - Circuit breaker
      - API key selection + rotation
      - Retry orchestration via execute_with_retry()
    """
    if not getattr(_ai_provider, '_is_valid', True):
        raise TerminalTaskError(f"INVALID_AI_ENDPOINT: {getattr(_ai_provider, '_invalid_reason', 'AI provider endpoint is invalid')}")

    from core.observability import observability, metrics

    # ── TENANT CONTEXT VALIDATION ──
    tenant_id = request_data.get('tenant_id') or (request_data.get('metadata') or {}).get('tenant_id')

    if not tenant_id or not isinstance(tenant_id, str) or tenant_id == 'None':
        logger.error(
            f"[TENANT_CONTEXT_INVALID] task_id={request_data.get('id')} "
            f"payload={json.dumps(request_data)[:200]}"
        )
        return {'error': 'Invalid or missing tenant_id', 'code': 'INVALID_TENANT_CONTEXT'}

    logger.info(f"[TENANT_CONTEXT_RESOLVED] tenant_id={tenant_id}")

    # ── Task 3: Conservative Simple Invoice Classifier ──
    SIMPLE_INVOICE_BYPASS_SHADOW_MODE = getattr(settings, 'SIMPLE_INVOICE_BYPASS_SHADOW_MODE', True)
    SIMPLE_INVOICE_BYPASS_ACTIVE = getattr(settings, 'SIMPLE_INVOICE_BYPASS_ACTIVE', False)
    
    # Force bypass disabled during Sprint 1
    if SIMPLE_INVOICE_BYPASS_ACTIVE:
        logger.warning("[SIMPLE_INVOICE_BYPASS_ACTIVE_OVERRIDE] Real bypass is forbidden in Sprint 1. Forcing active=False.")
        SIMPLE_INVOICE_BYPASS_ACTIVE = False

    bypass_payload = None
    if request_data.get('type') == 'extraction':
        ocr_text = request_data.get('_pdf_ocr_text')
        page_count = request_data.get('total_pages') or 1
        record_id = request_data.get('record_id') or (request_data.get('metadata') or {}).get('record_id')
        
        from ocr_pipeline.simple_invoice_classifier import classify_simple_invoice
        try:
            bypass_payload = classify_simple_invoice(ocr_text, page_count, tenant_id)
        except Exception as classifier_err:
            logger.error(f"[SIMPLE_INVOICE_CLASSIFIER_ERR] record={record_id} err={classifier_err}")

        # Real bypass: return candidate directly (Forbidden during Sprint 1, kept as structured safeguard)
        if bypass_payload and SIMPLE_INVOICE_BYPASS_ACTIVE and not SIMPLE_INVOICE_BYPASS_SHADOW_MODE:
            logger.critical(f"[SIMPLE_INVOICE_BYPASS_ACTIVE_TRIGGERED] record={record_id} Bypassing AI completely!")
            return {'reply': json.dumps(bypass_payload)}

    # ── OVERLOAD SHEDDING ──
    from core.sqs import queue_service
    import uuid
    q_depth = queue_service.get_queue_depth('ai')
    if q_depth > 5000:
        if random.random() < 0.5:
            logger.critical(f"[OVERLOAD_SHEDDING] Q_DEPTH={q_depth}. Dropping request for {tenant_id}")
            raise ProviderSaturatedError('AI service is under extreme load.')

    # ── DISTRIBUTED CONCURRENCY PERMIT ──
    permit_id = request_data.get('id', str(uuid.uuid4()))
    if not concurrency_governor.acquire_permit(permit_id, tenant_id):
        observability.ai_metric(event="TENANT_THROTTLED", tenant_id=tenant_id)
        metrics.increment_counter("ai:throttled", tags={"tenant": tenant_id})
        logger.warning(
            f"[AI_PROVIDER_THROTTLED] tenant_id={tenant_id} — AI system is at capacity."
        )
        raise ProviderSaturatedError('AI system is at capacity.')

    # ── RPS RATE LIMITING ──
    max_rps = int(os.getenv('AI_MAX_RPS', '10'))
    rate_limit_key = "ai_rate_limit:global"

    acquired_rate_limit = False
    for attempt in range(300):
        res = rate_limiter.check_rate_limit(rate_limit_key, limit=max_rps, window=1.0)
        if res.get('allowed'):
            acquired_rate_limit = True
            break
        sleep_time = res.get('retry_after') or 0.1
        time.sleep(min(sleep_time, 1.0))

    if not acquired_rate_limit:
        logger.error(f"[RATE_LIMIT_EXCEEDED] Global AI RPS limit of {max_rps} exceeded after 30s back-pressure.")
        raise ProviderSaturatedError('AI provider rate limit reached.')

    try:
        # ── MOCK MODE ──
        if os.getenv('MOCK_EXTRACTION_MODE', 'false').lower() == 'true':
            import random as _r
            time.sleep(_r.uniform(0.05, 0.2))
            mock_reply = {
                "invoice_no": f"MOCK-{_r.randint(1000, 9999)}",
                "invoice_date": "2024-05-15",
                "vendor_name": "Mock Stress Corp",
                "total_amount": 1234.56,
                "currency": "INR",
                "items": [{"description": "Mock Item", "quantity": 1, "rate": 1234.56, "amount": 1234.56}]
            }
            record_id = request_data.get('record_id') or (request_data.get('metadata') or {}).get('record_id')
            if record_id:
                try:
                    rescan_history_id = (
                        request_data.get('rescan_history_id')
                        or (request_data.get('metadata') or {}).get('rescan_history_id')
                    )
                    from ocr_pipeline.models import AIUsageAccounting
                    AIUsageAccounting.objects.create(
                        invoice_temp_ocr_id=record_id,
                        rescan_history_id=rescan_history_id,
                        prompt_tokens=600,
                        completion_tokens=200,
                        total_tokens=800,
                        cost=0.00014,
                    )
                except Exception as _ae:
                    logger.warning(f"[MOCK_USAGE_SAVE_ERR] {_ae}")
            return {'reply': json.dumps(mock_reply)}

        # ── CIRCUIT BREAKER ──
        if circuit_breaker.is_open():
            return {'error': 'AI service temporarily unavailable.', 'code': 'CIRCUIT_BREAKER'}

        # ── API KEY SELECTION ──
        api_key = api_key_manager.get_healthy_key()
        if not api_key:
            return {'error': 'No API keys available.'}

        # ── BUILD PROMPT PARTS FOR PROVIDER ──
        # Forward the full request_data — execute_with_retry() extracts prompt parts
        if request_data.get('type') == 'agent':
            # ── AGENT (CHAT) PATH ─────────────────────────────────────────────────
            # Agent calls must NOT go through execute_with_retry() + call_single()
            # because call_single() always sets the system message to:
            #   "Expert Indian GST invoice OCR. Return ONLY valid JSON ..."
            # That causes Qwen to wrap its chat reply in JSON (e.g. {"response": "..."}).
            # Instead, call the Qwen API directly here with a plain-text conversational
            # system prompt so the model responds in natural language.
            user_message = request_data.get('message', '')
            history = request_data.get('history', []) or []

            agent_system_prompt = (
                "You are a helpful AI accounting assistant for an Indian ERP system. "
                "Answer the user's question clearly and concisely in plain text. "
                "Do NOT wrap your reply in JSON, code blocks, or any structured format. "
                "Respond ONLY with natural language text."
            )

            agent_messages = [{"role": "system", "content": agent_system_prompt}]
            for h in history:
                role = h.get('role', 'user')
                if role == 'model':
                    role = 'assistant'
                agent_messages.append({"role": role, "content": h.get('text', '')})
            agent_messages.append({"role": "user", "content": user_message})

            from mistralai.client import Mistral
            mistral_key = api_key if api_key and api_key.strip() else os.getenv("MISTRAL_API_KEY")
            timeout_ms = int(os.getenv("MISTRAL_TIMEOUT_MS", "60000"))
            agent_client = Mistral(api_key=mistral_key, timeout_ms=timeout_ms)

            t_ai_start = time.time()
            observability.ai_metric(event="PARALLEL_AI_EXECUTION", tenant_id=tenant_id, status="START")

            try:
                # Map roles correctly: Mistral expects user, assistant, system
                mistral_messages = []
                for msg in agent_messages:
                    role = msg.get("role")
                    if role == "assistant":
                        role = "assistant"
                    mistral_messages.append({"role": role, "content": msg.get("content", "")})

                agent_resp = agent_client.chat.complete(
                    model=os.getenv('MISTRAL_CHAT_MODEL', 'mistral-large-latest'),
                    messages=mistral_messages,
                    max_tokens=1024,
                    temperature=0.7,
                )
                response_text = (agent_resp.choices[0].message.content or '').strip()
            except Exception as agent_err:
                logger.error(f"[AGENT_MISTRAL_ERROR] {agent_err}")
                response_text = "Sorry, I am having trouble connecting to the AI. Please try again."
        else:
            prompt_text = request_data.get('prompt', 'Extract data')

            # ── A/B INPUT MODE GATE ──────────────────────────────────────────────
            # When QWEN_INPUT_MODE=text, strip all image payloads so that Qwen
            # operates purely as a text-to-JSON model.  The prompt_text already
            # embeds the OCR content built by extraction.py.
            # When QWEN_INPUT_MODE=multimodal (default), the existing behaviour
            # is fully preserved — no change to the request structure.
            _qwen_input_mode = os.getenv("OCR_INPUT_MODE", "multimodal").strip().lower()
            logger.info(
                f"[AI_PROXY_INPUT_MODE] mode={_qwen_input_mode} "
                f"image_data_present={'yes' if request_data.get('image_data') else 'no'} "
                f"batch_images_present={'yes' if request_data.get('batch_images') else 'no'} "
                f"ocr_text_chars={len(request_data.get('_pdf_ocr_text', '') or '')} "
                f"prompt_chars={len(prompt_text)}"
            )

            if _qwen_input_mode == "text":
                # Text-only: build a plain string prompt, ignore any image payloads
                prompt = prompt_text
            elif 'batch_images' in request_data:
                # Batch mode — build Gemini-style list for backward compat with execute_with_retry
                prompt = [prompt_text]
                for img in request_data['batch_images']:
                    prompt.append({
                        'inline_data': {
                            'mime_type': img.get('mime_type', 'image/jpeg'),
                            'data': base64.b64decode(img['data'])
                        }
                    })
            elif 'image_data' in request_data:
                prompt = [
                    prompt_text,
                    {
                        'inline_data': {
                            'mime_type': request_data.get('mime_type', 'image/jpeg'),
                            'data': base64.b64decode(request_data['image_data'])
                        }
                    }
                ]
            else:
                prompt = prompt_text

            t_ai_start = time.time()
            observability.ai_metric(event="PARALLEL_AI_EXECUTION", tenant_id=tenant_id, status="START")
            response_text = execute_with_retry(prompt, request_data, api_key)
                # [SHADOW_MODE_DISABLED] Shadow mode execution and comparison removed.

        ai_latency = time.time() - t_ai_start
        observability.ai_metric(
            event="PARALLEL_AI_EXECUTION",
            tenant_id=tenant_id,
            status="COMPLETE",
            latency_s=round(ai_latency, 3)
        )

        circuit_breaker.record_success()
        observability.ai_metric(event="AI_LATENCY", tenant_id=tenant_id, latency_s=round(ai_latency, 3))
        metrics.record_latency("ai:latency", ai_latency, tags={"tenant": tenant_id})
        return {'reply': response_text}

    except Exception as e:
        circuit_breaker.record_failure()
        observability.ai_metric(event="AI_ERROR", tenant_id=tenant_id, error=str(e)[:200])
        metrics.increment_counter("ai:errors", tags={"tenant": tenant_id})
        return {'error': str(e)}
    finally:
        concurrency_governor.release_permit(permit_id, tenant_id)


# ═══════════════════════════════════════════════════════════════════════════════
# AI SERVICE PROXY (interface unchanged — same as former Gemini version)
# ═══════════════════════════════════════════════════════════════════════════════

class AIServiceProxy:
    def make_request(
        self,
        request_type: str,
        request_data: dict,
        user_id: str,
        tenant_id: str = None,
        metadata: dict = None,
        delay_seconds: int = 0,
    ) -> dict:
        if not getattr(_ai_provider, '_is_valid', True):
            err_msg = f"INVALID_AI_ENDPOINT: {getattr(_ai_provider, '_invalid_reason', 'AI provider endpoint is invalid')}"
            logger.error(f"[AI_ENQUEUE_REJECTED] {err_msg}")
            return {'error': err_msg, '_error': err_msg, 'code': 'INVALID_AI_ENDPOINT'}

        request_data.update({
            'type': request_type,
            'user_id': user_id,
            'tenant_id': tenant_id or 'anonymous'
        })
        if metadata:
            request_data['metadata'] = metadata

        wait_for_result = request_data.get('wait_for_result', True)

        if not wait_for_result:
            # ── ASYNC OFFLOADING TO SQS ──
            from vouchers.message_factory import message_factory

            session_id = request_data.get('upload_session_id') or (metadata.get('upload_session_id') if metadata else 'unknown')
            job_id = request_data.get('job_id') or (metadata.get('job_id') if metadata else 'unknown')
            record_id = request_data.get('record_id') or 'unknown'

            from copy import deepcopy
            msg = message_factory.create_message(
                task_type="AI_EXTRACTION",
                tenant_id=tenant_id,
                session_id=session_id,
                payload=request_data,
                correlation_id=metadata.get('correlation_id') if metadata else None
            )
            msg_copy = deepcopy(msg)

            from core.sqs import queue_service
            try:
                pushed = queue_service.push(msg_copy, queue_type='ai', delay_seconds=delay_seconds)
                if not pushed:
                    raise RuntimeError(
                        f"[SQS_PUSH_FAILED] push() returned False for msg_id={msg_copy['id']} record={record_id}"
                    )

                # Mark as successfully enqueued in Redis
                if record_id and record_id != 'unknown':
                    rec_id_str = str(record_id)
                    page_nums = []
                    single_page = request_data.get('page_number') or (metadata.get('page_index') if metadata else None)
                    if single_page is not None:
                        page_nums.append(str(single_page))

                    if 'page_index' in request_data and request_data['page_index'] is not None:
                        page_nums.append(str(request_data['page_index']))

                    if 'batch_indices' in request_data and request_data['batch_indices']:
                        page_nums.extend([str(idx + 1) for idx in request_data['batch_indices']])

                    # Deduplicate
                    seen = set()
                    page_nums = [x for x in page_nums if not (x in seen or seen.add(x))]

                    if page_nums:
                        from core.redis_orchestrator import orchestrator
                        for p_num in page_nums:
                            orchestrator.redis.set(
                                f"assembly:{rec_id_str}:page:{p_num}:enqueued", "true", ex=86400
                            )
                            orchestrator.redis.sadd(
                                f"assembly:{rec_id_str}:enqueued_success_pages", p_num
                            )
                        orchestrator.redis.expire(
                            f"assembly:{rec_id_str}:enqueued_success_pages", 86400
                        )

                logger.info(
                    f"[QUEUE_FORWARD_SUCCESS] target_queue=ai msg_id={msg_copy['id']} "
                    f"record={record_id} job={job_id}"
                )
            except Exception as e:
                logger.error(f"[QUEUE_FORWARD_FAILURE] target_queue=ai error={e}")
                raise

            logger.info(f"[AI_TASK_EMITTED] id={msg['id']} corr={msg['correlation_id']} session={session_id}")
            return {'status': 'queued', 'message': 'Task enqueued to AI specialized worker.'}

        return process_ai_request(request_data)

    def get_stats(self) -> dict:
        """Get service statistics."""
        return {
            'total_requests': 0,
            'cache_hits': 0,
            'circuit_breaker_open': circuit_breaker.is_open(),
            'api_keys_total': len(api_key_manager.api_keys),
            'api_keys_unhealthy': len(api_key_manager.unhealthy_keys),
            'provider': 'Mistral',
            'model': AI_MODEL_NAME,
        }


ai_service = AIServiceProxy()
