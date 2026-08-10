"""
Ollama Local Runtime Provider Client (Phase 18.1 Dynamic Token & Thread Hardening)
====================================================================================
Interfaces directly with self-hosted Ollama server REST API.
Includes:
- Dynamic context budgeting (num_ctx calculated based on prompt + reserve)
- Dynamic output token budgeting (num_predict configurable & adaptive)
- Persistent TCP connection pooling
- 300s model resolution caching
- Resident keep_alive tuning
- Telemetry logging for TTFT and total generation duration
"""
import requests
import json
import time
from typing import Generator, Dict, Any, List, Optional, Tuple
from core.kiki.providers.base_llm import BaseLLMProvider
from core.kiki.config import kiki_settings
from core.kiki.logging import get_kiki_logger
import threading
from core.kiki.runtime.token_budget_service import token_budget_service

logger = get_kiki_logger("ollama_client")





class OllamaClient(BaseLLMProvider):
    """Local Ollama LLM Provider implementation with Phase 18.3 dynamic token & concurrency controls."""
    
    _cached_models: List[str] = []
    _models_cached_at: float = 0.0
    _concurrency_semaphore = threading.Semaphore(getattr(kiki_settings, "OLLAMA_MAX_CONCURRENT_GENERATIONS", 4))

    def __init__(self, base_url: str = None):
        self.base_url = (base_url or kiki_settings.OLLAMA_BASE_URL).rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({"Connection": "keep-alive"})

    def _calculate_dynamic_context(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None
    ) -> Tuple[int, int]:
        """Calculates dynamic num_ctx and num_predict using exact subword token accounting."""
        budget = token_budget_service.calculate_request_budget(
            query=prompt,
            system_prompt=system_prompt,
            requested_output_tokens=max_tokens
        )
        return budget["num_ctx"], budget["num_predict"]


    def _get_available_model(self, requested_model: str) -> str:
        """Dynamically resolve requested model with 300-second in-memory caching to eliminate per-query HTTP overhead."""
        now = time.time()
        if not OllamaClient._cached_models or (now - OllamaClient._models_cached_at) > 300:
            try:
                resp = self.session.get(f"{self.base_url}/api/tags", timeout=3)
                if resp.status_code == 200:
                    OllamaClient._cached_models = [m.get("name") for m in resp.json().get("models", [])]
                    OllamaClient._models_cached_at = now
            except Exception:
                pass

        installed_models = OllamaClient._cached_models
        if installed_models:
            if requested_model in installed_models:
                return requested_model
            req_name = requested_model.split(':')[0].lower()
            for m in installed_models:
                if req_name in m.lower() or m.split(':')[0].lower() in req_name:
                    return m
            return installed_models[0]

        return requested_model

    def _calculate_dynamic_context(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None
    ) -> Tuple[int, int]:
        """
        Phase 18.1 Dynamic Token Budget Calculation:
        num_ctx = SYSTEM_TOKENS + PROMPT_TOKENS + OUTPUT_RESERVE + SAFETY_MARGIN (200 tokens)
        Bounded between OLLAMA_MIN_CTX (2048) and OLLAMA_MAX_CTX (8192).
        """
        sys_tokens = int(len((system_prompt or "").split()) * 1.3)
        prompt_tokens = int(len(prompt.split()) * 1.3)
        default_out = getattr(kiki_settings, "OLLAMA_DEFAULT_OUTPUT_TOKENS", 512)
        output_reserve = max_tokens if max_tokens is not None else default_out
        
        required_tokens = sys_tokens + prompt_tokens + output_reserve + 200
        min_ctx = getattr(kiki_settings, "OLLAMA_MIN_CTX", 2048)
        max_ctx = getattr(kiki_settings, "OLLAMA_MAX_CTX", 8192)
        
        dynamic_ctx = max(min_ctx, min(max_ctx, required_tokens))
        return dynamic_ctx, output_reserve

    def generate(
        self,
        model: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        stop_sequences: Optional[List[str]] = None,
        num_thread: Optional[int] = None
    ) -> str:
        target_model = self._get_available_model(model)
        dynamic_ctx, output_reserve = self._calculate_dynamic_context(
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=max_tokens
        )
        keep_alive = getattr(kiki_settings, "OLLAMA_KEEP_ALIVE", "60m")
        threads = num_thread or getattr(kiki_settings, "OLLAMA_NUM_THREAD", 8)

        payload = {
            "model": target_model,
            "prompt": prompt,
            "stream": False,
            "keep_alive": keep_alive,
            "options": {
                "temperature": temperature,
                "num_ctx": dynamic_ctx,
                "num_predict": output_reserve,
                "num_thread": threads,
            }
        }
        if system_prompt:
            payload["system"] = system_prompt
        if stop_sequences:
            payload["options"]["stop"] = stop_sequences

        t0 = time.time()
        try:
            with OllamaClient._concurrency_semaphore:
                resp = self.session.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                    timeout=kiki_settings.REASONING_TIMEOUT_SECONDS
                )

            if resp.status_code == 404:
                raise RuntimeError(f"Local Ollama model '{target_model}' not found.")
            resp.raise_for_status()
            res_json = resp.json()
            answer = res_json.get("response", "").strip()
            
            gen_duration_ms = round((time.time() - t0) * 1000, 2)
            eval_count = res_json.get("eval_count", 0)
            eval_duration_ns = res_json.get("eval_duration", 0)
            eval_ms = round(eval_duration_ns / 1e6, 2) if eval_duration_ns else 0.0

            logger.info(
                f"[OLLAMA GENERATE] Model: '{target_model}' | Duration: {gen_duration_ms}ms | "
                f"num_ctx: {dynamic_ctx} | num_predict: {output_reserve} | "
                f"eval_count: {eval_count} tokens ({eval_ms}ms)"
            )
            return answer
        except requests.exceptions.Timeout:
            raise KikiModelTimeoutException(
                f"Ollama model '{target_model}' timed out after {kiki_settings.REASONING_TIMEOUT_SECONDS}s."
            )
        except Exception as e:
            raise RuntimeError(f"Ollama inference error for model '{target_model}': {str(e)}")

    def generate_json(
        self,
        model: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        schema: Optional[Dict[str, Any]] = None,
        num_thread: Optional[int] = None
    ) -> Dict[str, Any]:
        target_model = self._get_available_model(model)
        dynamic_ctx, output_reserve = self._calculate_dynamic_context(
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=256
        )
        keep_alive = getattr(kiki_settings, "OLLAMA_KEEP_ALIVE", "60m")
        threads = num_thread or getattr(kiki_settings, "OLLAMA_NUM_THREAD", 8)

        payload = {
            "model": target_model,
            "prompt": prompt,
            "format": "json",
            "stream": False,
            "keep_alive": keep_alive,
            "options": {
                "temperature": 0.1,
                "num_ctx": dynamic_ctx,
                "num_predict": 256,
                "num_thread": threads,
            }
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            resp = self.session.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=kiki_settings.ROUTER_TIMEOUT_SECONDS
            )
            if resp.status_code == 404:
                return {}
            resp.raise_for_status()
            res_text = resp.json().get("response", "{}").strip()
            return json.loads(res_text)
        except json.JSONDecodeError:
            return {}
        except requests.exceptions.Timeout:
            raise KikiModelTimeoutException(f"Ollama JSON query for '{target_model}' timed out.")
        except Exception as e:
            raise RuntimeError(f"Ollama JSON query error: {str(e)}")

    def stream(
        self,
        model: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        num_thread: Optional[int] = None
    ) -> Generator[str, None, None]:
        target_model = self._get_available_model(model)
        dynamic_ctx, output_reserve = self._calculate_dynamic_context(
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=max_tokens
        )
        keep_alive = getattr(kiki_settings, "OLLAMA_KEEP_ALIVE", "60m")
        threads = num_thread or getattr(kiki_settings, "OLLAMA_NUM_THREAD", 8)

        payload = {
            "model": target_model,
            "prompt": prompt,
            "stream": True,
            "keep_alive": keep_alive,
            "options": {
                "temperature": temperature,
                "num_ctx": dynamic_ctx,
                "num_predict": output_reserve,
                "num_thread": threads,
            }
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            resp = self.session.post(
                f"{self.base_url}/api/generate",
                json=payload,
                stream=True,
                timeout=60
            )
            resp.raise_for_status()
            for line in resp.iter_lines():
                if line:
                    data = json.loads(line.decode('utf-8'))
                    token = data.get("response", "")
                    if token:
                        yield token
                    if data.get("done", False):
                        break
        except Exception as e:
            yield f"\n[Ollama Streaming Error: {str(e)}]"
