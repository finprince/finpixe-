"""
MistralStructuredProvider — Mistral Structured OCR & Chat completions Provider
=============================================================================
Implements BaseAIProvider using Mistral AI cloud APIs.

Configuration (set in .env):
    MISTRAL_API_KEY      = <your-api-key>
    MISTRAL_OCR_MODEL    = mistral-ocr-latest
    MISTRAL_CHAT_MODEL   = mistral-large-latest
    MISTRAL_COST_PER_PAGE = 0.0030
"""

import os
import json
import logging
import time
from typing import Optional, List
from pydantic import BaseModel, Field

from .base import BaseAIProvider

logger = logging.getLogger(__name__)

# Import TerminalTaskError lazily
_TERMINAL_ERROR_CLS = None

def _get_terminal_error():
    global _TERMINAL_ERROR_CLS
    if _TERMINAL_ERROR_CLS is None:
        from core.ai_proxy import TerminalTaskError
        _TERMINAL_ERROR_CLS = TerminalTaskError
    return _TERMINAL_ERROR_CLS


# ── SCHEMAS FOR STRUCTURED INVOICE EXTRACTION ───────────────────────────────

class MistralInvoiceHeaderSchema(BaseModel):
    vendor_name: Optional[str] = Field(default="", description="The name of the vendor/supplier")
    vendor_address: Optional[str] = Field(default="", description="The address of the vendor")
    billing_address: Optional[str] = Field(default="", description="The billing address/buyer address")
    vendor_gstin: Optional[str] = Field(default="", description="GSTIN of the vendor/supplier")
    vendor_state: Optional[str] = Field(default="", description="State of the vendor")
    place_of_supply: Optional[str] = Field(default="", description="Place of supply of the invoice")
    invoice_no: Optional[str] = Field(default="", description="Invoice number")
    invoice_date: Optional[str] = Field(default="", description="Invoice date")
    total_amount: Optional[float] = Field(default=0.0, description="Grand total amount")
    taxable_value: Optional[float] = Field(default=0.0, description="Total taxable value")
    cgst: Optional[float] = Field(default=0.0, description="Total CGST amount")
    sgst: Optional[float] = Field(default=0.0, description="Total SGST amount")
    igst: Optional[float] = Field(default=0.0, description="Total IGST amount")
    gst_taxability_type: Optional[str] = Field(default="", description="GST taxability type")
    gst_nature_of_transaction: Optional[str] = Field(default="", description="GST nature of transaction")
    sales_order_no: Optional[str] = Field(default="", description="Sales order number")
    irn: Optional[str] = Field(default="", description="Invoice Reference Number (IRN)")
    ack_no: Optional[str] = Field(default="", description="Acknowledgment number")
    ack_date: Optional[str] = Field(default="", description="Acknowledgment date")

class MistralInvoiceItemSchema(BaseModel):
    description: Optional[str] = Field(default="", description="Item description")
    hsn_code: Optional[str] = Field(default="", description="HSN/SAC code")
    quantity: Optional[float] = Field(default=None, description="Quantity")
    uom: Optional[str] = Field(default="", description="Unit of measurement")
    rate: Optional[float] = Field(default=None, description="Unit rate")
    discount_percent: Optional[float] = Field(default=0.0, description="Discount percentage")
    taxable_value: Optional[float] = Field(default=0.0, description="Taxable value")
    igst_rate: Optional[float] = Field(default=0.0, description="IGST rate percentage")
    igst_amount: Optional[float] = Field(default=0.0, description="IGST tax amount")
    cgst_rate: Optional[float] = Field(default=0.0, description="CGST rate percentage")
    cgst_amount: Optional[float] = Field(default=0.0, description="CGST tax amount")
    sgst_rate: Optional[float] = Field(default=0.0, description="SGST rate percentage")
    sgst_amount: Optional[float] = Field(default=0.0, description="SGST tax amount")
    cess_rate: Optional[float] = Field(default=None, description="Cess rate percentage")
    cess_amount: Optional[float] = Field(default=None, description="Cess tax amount")
    amount: Optional[float] = Field(default=0.0, description="Total item value")

class MistralStructuredInvoiceSchema(BaseModel):
    header: MistralInvoiceHeaderSchema
    items: List[MistralInvoiceItemSchema]


class MistralStructuredProvider(BaseAIProvider):
    """
    Mistral Structured OCR & Chat completions provider.
    """

    NON_RETRYABLE_PATTERNS = [
        "400", "401", "403", "404",
        "invalid api key", "api key not valid",
        "malformed", "invalid_argument",
        "permission_denied", "unauthenticated",
        "quota_disabled", "billing not enabled",
        "model not found", "model_not_found",
        "invalid_ai_endpoint",
    ]

    def __init__(self):
        self._is_valid = True
        self._invalid_reason = ""

    def mark_invalid(self, classification: str, reason: str):
        self._is_valid = False
        self._invalid_reason = f"{classification}: {reason}"

    def mark_valid(self):
        self._is_valid = True
        self._invalid_reason = ""

    def _get_client(self, api_key: str):
        if not getattr(self, '_is_valid', True):
            TerminalTaskError = _get_terminal_error()
            raise TerminalTaskError(f"INVALID_AI_ENDPOINT: {self._invalid_reason}")

        from mistralai.client import Mistral
        
        resolved_key = api_key or os.getenv("MISTRAL_API_KEY")
        if not resolved_key:
            TerminalTaskError = _get_terminal_error()
            raise TerminalTaskError("INVALID_AI_ENDPOINT: MISTRAL_API_KEY environment variable is missing.")

        return Mistral(api_key=resolved_key)

    def call_single(
        self,
        prompt_text: str,
        image_b64: Optional[str],
        mime_type: str,
        batch_images: Optional[List[dict]],
        request_data: dict,
        api_key: str,
        model_name: str,
        attempt_label: str = "Attempt 1",
    ) -> str:
        TerminalTaskError = _get_terminal_error()
        client = self._get_client(api_key)

        t_start = time.time()
        response_text = ""

        # Determine if we are in visual document annotation mode or text mode
        is_visual = bool(image_b64 or (batch_images and len(batch_images) > 0))

        try:
            if is_visual:
                # ── Visual Structured OCR ──
                from mistralai.extra import response_format_from_pydantic_model
                mistral_model = model_name or os.getenv("MISTRAL_OCR_MODEL", "mistral-ocr-latest")

                if image_b64:
                    document_payload = {
                        "type": "image_url",
                        "image_url": f"data:{mime_type};base64,{image_b64}"
                    }
                    page_count = 1
                else:
                    # Resolve first image in batch for single page wrapper
                    first_img = batch_images[0]
                    document_payload = {
                        "type": "image_url",
                        "image_url": f"data:{first_img.get('mime_type', 'image/jpeg')};base64,{first_img.get('data')}"
                    }
                    page_count = len(batch_images)

                logger.info(f"📡 Mistral OCR dispatch: model={mistral_model} pages={page_count}")
                response = client.ocr.process(
                    model=mistral_model,
                    document=document_payload,
                    document_annotation_format=response_format_from_pydantic_model(MistralStructuredInvoiceSchema),
                    document_annotation_prompt=prompt_text
                )

                # Extract the parsed string annotation
                response_text = getattr(response, "document_annotation", "")
                if not response_text:
                    raise ValueError("Mistral OCR returned empty document annotation.")

                # Cost parameterization (flat rate per page)
                page_rate = float(os.getenv("MISTRAL_COST_PER_PAGE", "0.0030"))
                cost = page_rate * page_count

                # Usage info accounting
                prompt_tokens = 0
                completion_tokens = 0
                total_tokens = 0
                usage_info = getattr(response, "usage_info", None)
                if usage_info:
                    prompt_tokens = getattr(usage_info, "prompt_tokens", 0)
                    completion_tokens = getattr(usage_info, "completion_tokens", 0)
                    total_tokens = getattr(usage_info, "total_tokens", 0)

            else:
                # ── Text Completion Mode (NLP Reports view & Bank Statements text chunks) ──
                mistral_model = model_name or os.getenv("MISTRAL_CHAT_MODEL", "mistral-large-latest")
                logger.info(f"📡 Mistral Chat completions dispatch: model={mistral_model}")

                messages = [{"role": "user", "content": prompt_text}]
                
                # Check if JSON format requested
                req_type = request_data.get('type')
                is_json = (req_type in ('extraction', 'parameter_parse')) or ("json" in prompt_text.lower())
                response_format = {"type": "json_object"} if is_json else None

                response = client.chat.complete(
                    model=mistral_model,
                    messages=messages,
                    response_format=response_format
                )

                response_text = response.choices[0].message.content

                # Cost parameterization (token-based pricing for chat completions)
                prompt_rate = float(os.getenv("MISTRAL_CHAT_PROMPT_RATE", "2.0")) / 1_000_000
                completion_rate = float(os.getenv("MISTRAL_CHAT_COMPLETION_RATE", "6.0")) / 1_000_000
                
                prompt_tokens = response.usage.prompt_tokens
                completion_tokens = response.usage.completion_tokens
                total_tokens = response.usage.total_tokens
                
                cost = (prompt_tokens * prompt_rate) + (completion_tokens * completion_rate)

            # Record metrics & usage accounting
            from core.observability import metrics
            metrics.increment_counter("ai:tokens", total_tokens)
            metrics.record_latency("ai:cost", cost)

            record_id = (
                request_data.get("record_id")
                or (request_data.get("metadata") or {}).get("record_id")
            )
            if record_id:
                rescan_history_id = (
                    request_data.get("rescan_history_id")
                    or (request_data.get("metadata") or {}).get("rescan_history_id")
                )
                from ocr_pipeline.models import AIUsageAccounting
                AIUsageAccounting.objects.create(
                    invoice_temp_ocr_id=record_id,
                    rescan_history_id=rescan_history_id,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    cost=cost,
                )

            latency = time.time() - t_start
            logger.info(f"⚡ [MISTRAL_PERF] model={mistral_model} latency={latency:.2f}s cost=${cost:.5f}")

            return response_text

        except Exception as exc:
            err_msg = str(exc).lower()
            # Catch API errors to raise TerminalTaskError if appropriate
            is_terminal = any(pat in err_msg for pat in self.NON_RETRYABLE_PATTERNS)
            if is_terminal:
                raise TerminalTaskError(f"MISTRAL_TERMINAL_ERROR: {str(exc)}")
            raise exc

    def get_model_name(self) -> str:
        return os.getenv("MISTRAL_OCR_MODEL", "mistral-ocr-latest")

    def recheck_key_health(self, api_key: str, model_name: str) -> bool:
        try:
            client = self._get_client(api_key)
            # Fetch model list to verify key reachability
            client.models.list()
            return True
        except Exception:
            return False
