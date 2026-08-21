import re
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

def normalize_company_name(name: str) -> str:
    """
    Normalizes company names for comparison by:
    - Removing punctuation and special characters
    - Standardizing abbreviations (PVT LTD, PRIVATE LIMITED, LTD, LIMITED, etc.)
    - Converting & to AND
    - Collapsing multiple spaces and uppercasing
    """
    if not name:
        return ""
    s = str(name).upper().strip()
    s = re.sub(r'[&]', ' AND ', s)
    # Remove dots and commas
    s = re.sub(r'[\.,\-\/\\\(\)\[\]]', ' ', s)
    # Standardize legal suffixes
    s = re.sub(r'\bPRIVATE\s+LIMITED\b', 'PVTLTD', s)
    s = re.sub(r'\bPVT\s+LTD\b', 'PVTLTD', s)
    s = re.sub(r'\bPVTLTD\b', ' ', s)
    s = re.sub(r'\bLIMITED\b', ' ', s)
    s = re.sub(r'\bLTD\b', ' ', s)
    s = re.sub(r'\bPRIVATE\b', ' ', s)
    s = re.sub(r'\bPVT\b', ' ', s)
    s = re.sub(r'\bLLP\b', ' ', s)
    s = re.sub(r'\bINC\b', ' ', s)
    s = re.sub(r'\bCORP\b', ' ', s)
    s = re.sub(r'\bCO\b', ' ', s)
    # Remove any non-alphanumeric characters
    s = re.sub(r'[^A-Z0-9\s]', '', s)
    return " ".join(s.split())

def normalize_gstin_exact(g: Any) -> str:
    """
    Strict 15-character GSTIN normalizer:
    - Trim whitespace
    - Uppercase
    - Remove all internal whitespace
    - Normalizes common optical transcription confusion at position 13 ('I'/'L' -> '1', 'O' -> '0')
    """
    if not g:
        return ""
    s = "".join(str(g).split()).upper()
    s = re.sub(r'[^A-Z0-9]', '', s)
    if len(s) == 15:
        chars = list(s)
        if chars[12] in ('I', 'L'):
            chars[12] = '1'
        elif chars[12] == 'O':
            chars[12] = '0'
        return "".join(chars)
    return s

def validate_customer_against_tenant(
    tenant_or_id,
    buyer_name: str,
    buyer_gstin: str,
    record_id=None,
    invoice_no="",
    bill_to: str = ""
) -> Dict[str, Any]:
    """
    Dedicated validation of Buyer / Customer identity against logged-in Tenant / Company master.

    For a PURCHASE invoice:
      - Supplier / Vendor -> Sells to us
      - Customer / Buyer   -> OUR COMPANY

    MATCHING RULE:
      Customer Name MATCH AND Customer GSTIN MATCH
              ↓
      Our company invoice (Valid purchase)
              ↓
      DO NOT show company confirmation (company_match_detected = False)

      If either one does not match, or is missing:
              ↓
      Show "Is this our company invoice?" confirmation (company_match_detected = True)
    """
    tenant = None
    tenant_id_str = ""
    candidate_tenant_names = []
    candidate_tenant_gstins = []

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
            t_name = tenant_or_id.get("name") or tenant_or_id.get("company_name") or ""
            t_gstin = tenant_or_id.get("gstin") or ""
            tenant_id_str = str(tenant_or_id.get("id") or "")
            if t_name:
                candidate_tenant_names.append(t_name)
            if t_gstin:
                candidate_tenant_gstins.append(t_gstin)

    if tenant:
        # Collect current tenant/branch name and GSTIN
        t_name = (getattr(tenant, "name", "") or getattr(tenant, "company_name", "") or "").strip()
        t_gstin = (getattr(tenant, "gstin", "") or "").strip()
        b_name = (getattr(tenant, "branch_name", "") or "").strip()
        if t_name:
            candidate_tenant_names.append(t_name)
        if b_name:
            candidate_tenant_names.append(b_name)
        if t_gstin:
            candidate_tenant_gstins.append(t_gstin)

    # Fallback to system-wide company settings only if tenant object has empty details
    if not candidate_tenant_gstins or not candidate_tenant_names:
        try:
            from core.models import Branch
            primary_branch = Branch.objects.first()
            if primary_branch:
                if primary_branch.name and primary_branch.name not in candidate_tenant_names:
                    candidate_tenant_names.append(primary_branch.name)
                if primary_branch.gstin and primary_branch.gstin not in candidate_tenant_gstins:
                    candidate_tenant_gstins.append(primary_branch.gstin)
        except Exception:
            pass

    # Normalize buyer details with bill_to fallback if buyer_name is an address token
    effective_buyer_name = buyer_name or ""
    from ocr_pipeline.normalize import extract_buyer_name_from_bill_to, is_address_token
    if (not effective_buyer_name or is_address_token(effective_buyer_name) or effective_buyer_name.lower() in ('tamil nadu', 'coimbatore', 'kerala', 'karnataka', 'maharashtra', 'delhi')) and bill_to:
        recovered = extract_buyer_name_from_bill_to(str(bill_to))
        if recovered and not is_address_token(recovered):
            effective_buyer_name = recovered

    from vendors.vendor_validation_logic import canonicalize_gstin_ocr
    raw_b_gstin = canonicalize_gstin_ocr(buyer_gstin).strip().upper() if buyer_gstin else ""
    norm_buyer_gstin = normalize_gstin_exact(raw_b_gstin)
    clean_buyer_name = normalize_company_name(effective_buyer_name)

    # Check presence
    has_buyer_name = bool(clean_buyer_name and len(clean_buyer_name) >= 2 and effective_buyer_name.strip() not in ('—', '-', 'N/A', 'NA', 'NULL', 'NONE'))
    has_buyer_gstin = bool(norm_buyer_gstin and len(norm_buyer_gstin) == 15)

    norm_tenant_gstins = [normalize_gstin_exact(g) for g in candidate_tenant_gstins if g]
    norm_tenant_gstins = [g for g in norm_tenant_gstins if len(g) == 15]
    clean_tenant_names = [normalize_company_name(n) for n in candidate_tenant_names if n]
    clean_tenant_names = [n for n in clean_tenant_names if n]

    has_tenant_name = bool(clean_tenant_names)
    has_tenant_gstin = bool(norm_tenant_gstins)

    # Perform exact name comparison (or strong bidirectional token match for normalized names)
    name_matched = False
    if has_buyer_name and has_tenant_name:
        for t_name in clean_tenant_names:
            if clean_buyer_name == t_name:
                name_matched = True
                break
            elif len(clean_buyer_name) >= 4 and len(t_name) >= 4:
                if clean_buyer_name in t_name or t_name in clean_buyer_name:
                    name_matched = True
                    break

    # Perform exact GSTIN comparison (strict 15-char equality)
    gstin_matched = False
    if has_buyer_gstin and has_tenant_gstin:
        for t_gstin in norm_tenant_gstins:
            if norm_buyer_gstin == t_gstin:
                gstin_matched = True
                break

    # ── CANONICAL MATCHING LOGIC ─────────────────────────────────────────────
    # Customer Name MATCH AND Customer GSTIN MATCH
    #   -> Our company invoice -> DO NOT show company confirmation (company_match_detected = False)
    # If either one does not match (or missing):
    #   -> Show "Is this our company invoice?" confirmation (company_match_detected = True)
    # ─────────────────────────────────────────────────────────────────────────
    both_matched = (name_matched and gstin_matched)

    if both_matched:
        company_match_detected = False
        company_match_decision = "SELF_COMPANY"
        customer_status = "SELF_COMPANY"
    else:
        company_match_detected = True
        if gstin_matched and not name_matched:
            company_match_decision = "GSTIN_MATCH_NAME_MISMATCH"
            customer_status = "NAME_MISMATCH"
        elif name_matched and not gstin_matched:
            company_match_decision = "NAME_MATCH_GSTIN_MISMATCH"
            customer_status = "GSTIN_MISMATCH"
        elif not has_buyer_name and not has_buyer_gstin:
            company_match_decision = "CUSTOMER_IDENTITY_MISSING"
            customer_status = "IDENTITY_UNKNOWN"
        elif not has_buyer_gstin:
            company_match_decision = "BUYER_GSTIN_MISSING"
            customer_status = "GSTIN_MISSING"
        elif not has_buyer_name:
            company_match_decision = "BUYER_NAME_MISSING"
            customer_status = "NAME_MISSING"
        else:
            company_match_decision = "EXTERNAL_CUSTOMER"
            customer_status = "EXTERNAL_CUSTOMER"

    # If mismatch detected, check if user previously approved this specific record with PROCEED
    if company_match_detected and tenant_id_str and record_id:
        try:
            from pending_purchases.models import PendingPurchase
            from ocr_pipeline.models import InvoiceTempOCR

            already_proceeded = False
            if str(record_id).isdigit():
                if InvoiceTempOCR.objects.filter(id=int(record_id), tenant_id=tenant_id_str, extracted_data__company_match_decision='PROCEED').exists():
                    already_proceeded = True
                elif PendingPurchase.objects.filter(id=int(record_id), company_id=tenant_id_str, company_match_decision='PROCEED').exists():
                    already_proceeded = True
            else:
                if InvoiceTempOCR.objects.filter(file_hash=str(record_id), tenant_id=tenant_id_str, extracted_data__company_match_decision='PROCEED').exists():
                    already_proceeded = True

            if already_proceeded:
                logger.info(
                    f"[CUSTOMER_VALIDATION_RECORD_PROCEED] record_id='{record_id}' tenant='{tenant_id_str}' "
                    f"previously marked PROCEED by user -> keeping PROCEED state"
                )
                company_match_detected = False
                company_match_decision = "PROCEED"
                customer_status = "SELF_COMPANY"
        except Exception as e:
            logger.warning(f"[CUSTOMER_VALIDATION_RECORD_CHECK_ERR] {e}")

    logger.info(
        f"[CUSTOMER_VALIDATION] "
        f"record_id={record_id} "
        f"invoice_no='{invoice_no}' "
        f"tenant_id='{tenant_id_str}' "
        f"buyer_name='{buyer_name}' (norm='{clean_buyer_name}') "
        f"buyer_gstin='{buyer_gstin}' (norm='{norm_buyer_gstin}') "
        f"tenant_names={candidate_tenant_names} "
        f"tenant_gstins={candidate_tenant_gstins} "
        f"name_match={name_matched} "
        f"gstin_match={gstin_matched} "
        f"customer_status='{customer_status}' "
        f"company_match_detected={company_match_detected} "
        f"company_match_decision='{company_match_decision}'"
    )

    primary_tenant_name = candidate_tenant_names[0] if candidate_tenant_names else ""
    primary_tenant_gstin = candidate_tenant_gstins[0] if candidate_tenant_gstins else ""

    return {
        "customer_status": customer_status,
        "company_match_detected": company_match_detected,
        "company_match_decision": company_match_decision,
        "name_matched": name_matched,
        "gstin_matched": gstin_matched,
        "buyer_name": buyer_name,
        "buyer_gstin": norm_buyer_gstin,
        "customer_name": buyer_name,
        "customer_gstin": norm_buyer_gstin,
        "raw_buyer_name": buyer_name,
        "canonical_buyer_name": clean_buyer_name,
        "canonical_buyer_gstin": norm_buyer_gstin,
        "tenant_name": primary_tenant_name,
        "tenant_gstin": primary_tenant_gstin
    }

