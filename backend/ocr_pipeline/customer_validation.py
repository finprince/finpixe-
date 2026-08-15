import re
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

def validate_customer_against_tenant(
    tenant_or_id,
    buyer_name: str,
    buyer_gstin: str,
    record_id=None,
    invoice_no=""
) -> Dict[str, Any]:
    """
    Dedicated validation of Buyer / Customer identity against logged-in Tenant / Company.

    DECISION MATRIX:
    - CASE 1: buyer GSTIN == tenant GSTIN AND buyer name == tenant company name
      -> company_match_detected = True, company_match_decision = "SELF_COMPANY", customer_status = "SELF_COMPANY"
    - CASE 2: buyer GSTIN != tenant GSTIN (both present)
      -> company_match_detected = False, company_match_decision = "EXTERNAL_CUSTOMER", customer_status = "EXTERNAL_CUSTOMER"
    - CASE 3: buyer GSTIN == tenant GSTIN BUT buyer name differs
      -> company_match_detected = True, company_match_decision = "GSTIN_MATCH_NAME_MISMATCH", customer_status = "NAME_MISMATCH"
    - CASE 4: buyer GSTIN missing BUT buyer name matches tenant company name
      -> company_match_detected = False, company_match_decision = "NAME_ONLY_MATCH", customer_status = "NAME_ONLY_MATCH"
    - CASE 5: both buyer name and buyer GSTIN missing
      -> company_match_detected = False, company_match_decision = "CUSTOMER_IDENTITY_MISSING", customer_status = "IDENTITY_UNKNOWN"
    - CASE 6: tenant identity missing/incomplete
      -> company_match_detected = False, company_match_decision = "TENANT_IDENTITY_MISSING", customer_status = "IDENTITY_UNKNOWN"
    """
    tenant = None
    tenant_name = ""
    tenant_gstin = ""
    tenant_id_str = ""

    if tenant_or_id:
        if isinstance(tenant_or_id, str):
            tenant_id_str = tenant_or_id
            try:
                from core.models import Tenant
                tenant = Tenant.objects.filter(id=tenant_id_str).first()
            except Exception as e:
                logger.warning(f"[TENANT_LOOKUP_ERR] tenant_id={tenant_id_str}: {e}")
        elif hasattr(tenant_or_id, "id"):
            tenant = tenant_or_id
            tenant_id_str = str(tenant.id)
        elif isinstance(tenant_or_id, dict):
            tenant_name = tenant_or_id.get("name") or tenant_or_id.get("company_name") or ""
            tenant_gstin = tenant_or_id.get("gstin") or ""
            tenant_id_str = str(tenant_or_id.get("id") or "")

    if tenant:
        tenant_name = (getattr(tenant, "name", "") or getattr(tenant, "company_name", "") or "").strip()
        tenant_gstin = (getattr(tenant, "gstin", "") or "").strip().upper()

    from vendors.vendor_validation_logic import canonicalize_gstin_ocr

    canonical_buyer_gstin = canonicalize_gstin_ocr(buyer_gstin).strip().upper() if buyer_gstin else ""
    canonical_tenant_gstin = canonicalize_gstin_ocr(tenant_gstin).strip().upper() if tenant_gstin else ""

    def normalize_gstin_for_comparison(g: str) -> str:
        if not g:
            return ""
        g = "".join(str(g).split()).upper()
        if len(g) == 15:
            chars = list(g)
            if chars[12] in ('I', 'L'):
                chars[12] = '1'
            elif chars[12] == 'O':
                chars[12] = '0'
            return "".join(chars)
        return g

    comp_buyer_gstin = normalize_gstin_for_comparison(canonical_buyer_gstin)
    comp_tenant_gstin = normalize_gstin_for_comparison(canonical_tenant_gstin)

    clean_tenant_name = re.sub(r'\s+', ' ', re.sub(r'[^a-zA-Z0-9\s]', '', str(tenant_name or ''))).strip().upper()
    clean_buyer_name = re.sub(r'\s+', ' ', re.sub(r'[^a-zA-Z0-9\s]', '', str(buyer_name or ''))).strip().upper()

    name_matched = False
    gstin_matched = False

    if clean_tenant_name and clean_buyer_name:
        if clean_buyer_name == clean_tenant_name:
            name_matched = True
        elif len(clean_buyer_name) >= 4 and len(clean_tenant_name) >= 4:
            if clean_buyer_name in clean_tenant_name or clean_tenant_name in clean_buyer_name:
                name_matched = True

    if comp_tenant_gstin and comp_buyer_gstin and len(comp_tenant_gstin) == 15 and len(comp_buyer_gstin) == 15:
        if comp_buyer_gstin == comp_tenant_gstin:
            gstin_matched = True

    has_tenant_gstin = bool(canonical_tenant_gstin and len(canonical_tenant_gstin) == 15)
    has_buyer_gstin = bool(canonical_buyer_gstin and len(canonical_buyer_gstin) == 15)
    has_tenant_name = bool(clean_tenant_name)
    has_buyer_name = bool(clean_buyer_name)

    company_match_detected = False
    company_match_decision = "CUSTOMER_IDENTITY_MISSING"
    customer_status = "IDENTITY_UNKNOWN"

    if not has_tenant_gstin and not has_tenant_name:
        company_match_detected = False
        company_match_decision = "TENANT_IDENTITY_MISSING"
        customer_status = "IDENTITY_UNKNOWN"
    elif not has_buyer_gstin and not has_buyer_name:
        company_match_detected = False
        company_match_decision = "CUSTOMER_IDENTITY_MISSING"
        customer_status = "IDENTITY_UNKNOWN"
    elif has_buyer_gstin and has_tenant_gstin:
        if gstin_matched:
            if name_matched or not has_buyer_name:
                # CASE 1: Both GSTIN and Name Match (or Name not extracted but GSTIN matches)
                # Invoice belongs to own company -> Valid purchase, DO NOT ask proceed/not proceed
                company_match_detected = False
                company_match_decision = "SELF_COMPANY"
                customer_status = "SELF_COMPANY"
            else:
                # CASE 2: Same GSTIN, Different Name -> Name Mismatch -> ASK proceed/not proceed
                company_match_detected = True
                company_match_decision = "GSTIN_MATCH_NAME_MISMATCH"
                customer_status = "NAME_MISMATCH"
        else:
            # CASE 3: Different GSTIN -> Company Mismatch / External Customer -> ASK proceed/not proceed
            company_match_detected = True
            company_match_decision = "EXTERNAL_CUSTOMER"
            customer_status = "EXTERNAL_CUSTOMER"
    elif has_buyer_name and not has_buyer_gstin:
        if has_tenant_name:
            if name_matched:
                # CASE 4: Missing buyer GSTIN, Name matches tenant -> Valid purchase, DO NOT ask
                company_match_detected = False
                company_match_decision = "NAME_ONLY_MATCH"
                customer_status = "SELF_COMPANY"
            else:
                # CASE 5: Missing buyer GSTIN, Name differs -> Mismatch -> ASK proceed/not proceed
                company_match_detected = True
                company_match_decision = "EXTERNAL_CUSTOMER"
                customer_status = "EXTERNAL_CUSTOMER"
        else:
            company_match_detected = False
            company_match_decision = "TENANT_IDENTITY_MISSING"
            customer_status = "IDENTITY_UNKNOWN"
    elif has_buyer_gstin and not has_tenant_gstin:
        company_match_detected = False
        company_match_decision = "TENANT_GSTIN_MISSING"
        customer_status = "IDENTITY_UNKNOWN"

    logger.info(
        f"[CUSTOMER_VALIDATION] "
        f"record_id={record_id} "
        f"invoice_no='{invoice_no}' "
        f"tenant_id='{tenant_id_str}' "
        f"buyer_name='{buyer_name}' "
        f"canonical_buyer_name='{clean_buyer_name}' "
        f"buyer_gstin='{buyer_gstin}' "
        f"canonical_buyer_gstin='{canonical_buyer_gstin}' "
        f"tenant_company_name='{tenant_name}' "
        f"tenant_company_gstin='{tenant_gstin}' "
        f"name_match={name_matched} "
        f"gstin_match={gstin_matched} "
        f"customer_status='{customer_status}' "
        f"company_match_detected={company_match_detected} "
        f"company_match_decision='{company_match_decision}'"
    )

    return {
        "customer_status": customer_status,
        "company_match_detected": company_match_detected,
        "company_match_decision": company_match_decision,
        "name_matched": name_matched,
        "gstin_matched": gstin_matched,
        "buyer_name": buyer_name,
        "buyer_gstin": canonical_buyer_gstin,
        "customer_name": buyer_name,
        "customer_gstin": canonical_buyer_gstin,
        "raw_buyer_name": buyer_name,
        "canonical_buyer_name": clean_buyer_name,
        "canonical_buyer_gstin": canonical_buyer_gstin,
        "tenant_name": tenant_name,
        "tenant_gstin": tenant_gstin
    }
