import os
import sys
import django
import json
import base64
import hashlib
import time

def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    django.setup()

    from ocr_pipeline.isolated_ocr_service import run_isolated_page_extraction
    from ocr_pipeline.extraction import _repair_json
    from ocr_pipeline.normalize import get_canonical_export_record, get_normalized_items
    from ocr_pipeline.models import AICache
    from mistralai.client import Mistral
    from mistralai.extra import response_format_from_pydantic_model
    from core.providers.mistral_structured_provider import MistralStructuredInvoiceSchema, MistralStructuredProvider

    pdf_path = r"c:\108\AI-accounting-0.03\backend\media\bulk_pipeline\ocr\2eda0ac6-6af2-493e-8792-bc973fe946b7\ec956bb9-8170-4462-b723-c6a65ce6bc6e\c2ab2f6b5da0b8f9d2e1a86cb4b88c1549439c1bdbe3df267d59c689f529675a_IMG_20260406_0003.pdf"
    page_idx = 13  # Page 14

    print("=== STARTING INSTRUMENTED INVOICE EXTRACTION TRACE ===")
    
    # ── SNAPSHOT 1 ──
    print("\n" + "="*40 + "\nSNAPSHOT 1: EXACT OCR TEXT SENT TO AI\n" + "="*40)
    iso_res = run_isolated_page_extraction(pdf_path, page_idx)
    page_ocr_text = iso_res.get("text", "")
    print(page_ocr_text)

    # ── SNAPSHOT 2 ──
    print("\n" + "="*40 + "\nSNAPSHOT 2: IMMEDIATELY BEFORE call_single()\n" + "="*40)
    schema_str = """{"header":{"vendor_name":"","vendor_address":"","billing_address":"","vendor_gstin":"","vendor_state":"","place_of_supply":"","invoice_no":"","invoice_date":"","total_amount":0,"taxable_value":0,"cgst":0,"sgst":0,"igst":0,"gst_taxability_type":"Taxable","gst_nature_of_transaction":"","sales_order_no":"","irn":"","ack_no":"","ack_date":""},"items":[{"description":"","hsn_code":"","quantity":0,"uom":"","rate":0,"discount_percent":0,"taxable_value":0,"igst_rate":0,"igst_amount":0,"cgst_rate":0,"cgst_amount":0,"sgst_rate":0,"sgst_amount":0,"cess_rate":0,"cess_amount":0,"amount":0}]}"""
    base_prompt = f"""Extract PURCHASE invoice data into this exact JSON schema:

{schema_str}

RULES:
1. vendor_address = "Consignee/Ship To" block; billing_address = "Buyer/Bill To" block only. Never mix them. Null if absent.
2. invoice_no: prefer label "Invoice No"/"Bill No", near top/date, must have >= 1 digit, 3-25 chars.
3. Line Item Columns:
   Extract the columns exactly as printed on the invoice for each item:
   - 'amount': Extract from the column labeled 'Amount', 'Value', or 'Total' exactly as printed.
   - 'taxable_value': Extract from the column explicitly labeled 'Taxable Value', 'Taxable Amount', or 'Assessable Value' if and only if such a column is printed. Otherwise, leave as null. Do NOT calculate or derive it.
   - 'discount_percent': Extract from the column explicitly labeled 'Disc.%', 'Discount %' if printed. Do NOT calculate or infer.
   - 'discount_amount': Extract from the column explicitly labeled 'Discount' or 'Disc. Amt' if printed. Do NOT calculate or infer.
   - 'rate'/'quantity'/'cgst_rate'/'sgst_rate'/'igst_rate': Extract values exactly as printed.
   Do NOT perform arithmetic operations, do NOT subtract GST, and do NOT attempt to reconcile layout semantics. The backend will handle calculations.
4. HSN/SAC and UOM per item if visible.
5. Continuation page: extract invoice_no and vendor_name from top labels; markers: "continued","amount chargeable","authorised signatory","rounded off".
6. Missing field -> null. No hallucination. All numeric fields must be numbers.
7. OCR text is the primary source of truth. Extract values exactly as they appear unless a rule above requires transformation.
8. Do not invent or infer values that are not supported by the OCR text. If a field is ambiguous or absent, return null.
9. Preserve line-item order exactly as it appears in the document.
Return ONLY valid JSON.
"""
    page_isolated_prompt = f"{base_prompt}\n\n### [PAGE {page_idx+1} OCR DATA]\n{page_ocr_text}"
    img_bytes = iso_res["image_bytes"]
    file_b64 = base64.b64encode(img_bytes).decode('utf-8')

    request_payload = {
        "model": "mistral-ocr-latest",
        "document": {
            "type": "image_url",
            "image_url": f"data:image/jpeg;base64,{file_b64[:100]}... [TRUNCATED]"
        },
        "document_annotation_format": "PydanticSchema(MistralStructuredInvoiceSchema)",
        "document_annotation_prompt": "[PROMPT TEXT SHOWN IN SNAPSHOT 1 & 2]"
    }

    print(f"PROMPT CHARS: {len(page_isolated_prompt)}")
    print(f"SCHEMA TYPE: MistralStructuredInvoiceSchema")
    print(f"REQUEST PAYLOAD DETAILS: {json.dumps(request_payload, indent=2)}")

    # ── SNAPSHOT 3 ──
    print("\n" + "="*40 + "\nSNAPSHOT 3: COMPLETE RAW RESPONSE BODY FROM MISTRAL\n" + "="*40)
    api_key = os.getenv("MISTRAL_API_KEY")
    client = Mistral(api_key=api_key)
    document_payload_full = {
        "type": "image_url",
        "image_url": f"data:image/jpeg;base64,{file_b64}"
    }

    # Perform the live API call
    response = client.ocr.process(
        model="mistral-ocr-latest",
        document=document_payload_full,
        document_annotation_format=response_format_from_pydantic_model(MistralStructuredInvoiceSchema),
        document_annotation_prompt=page_isolated_prompt
    )
    raw_response_body = response.model_dump_json(indent=2)
    print(raw_response_body)

    # ── SNAPSHOT 4 ──
    print("\n" + "="*40 + "\nSNAPSHOT 4: IMMEDIATELY AFTER _repair_json()\n" + "="*40)
    raw_text = getattr(response, "document_annotation", "")
    repaired_text, repair_strategy, repair_err = _repair_json(raw_text, record_id=999, page=page_idx+1)
    
    # Parse repaired
    parsed_json = json.loads(repaired_text)
    items = parsed_json.get("items", [])
    for idx, item in enumerate(items):
        print(f"Item {idx}: description='{item.get('description')}' | HSN={item.get('hsn_code')} | cgst_rate={item.get('cgst_rate')} | sgst_rate={item.get('sgst_rate')} | igst_rate={item.get('igst_rate')}")
        
    print(f"Repair Strategy Used: {repair_strategy}")
    print(f"Repair Error Details: {repair_err}")

    # Compare with Snapshot 3
    print("\nComparison of Snapshot 4 parsed values vs Snapshot 3 raw strings:")
    # We parsed it from Snapshot 3
    raw_parsed = json.loads(raw_text)
    raw_items = raw_parsed.get("items", [])
    for idx, (raw_itm, rep_itm) in enumerate(zip(raw_items, items)):
        print(f"Item {idx}:")
        print(f"  Raw (Snapshot 3) -> cgst_rate={raw_itm.get('cgst_rate')} sgst_rate={raw_itm.get('sgst_rate')}")
        print(f"  Repaired (Snapshot 4) -> cgst_rate={rep_itm.get('cgst_rate')} sgst_rate={rep_itm.get('sgst_rate')}")

    # ── SNAPSHOT 5 ──
    print("\n" + "="*40 + "\nSNAPSHOT 5: IMMEDIATELY BEFORE WRITING AICache\n" + "="*40)
    # Replicate payload structure
    cache_payload = dict(parsed_json)
    cache_payload["_pdf_ocr_text"] = page_ocr_text
    cache_payload["_raw_text"] = raw_text
    
    # Exclude underscore keys for raw clone
    raw_clone = {k: cache_payload[k] for k in cache_payload if not k.startswith('_')}
    cache_payload["_raw_extraction"] = raw_clone
    
    print("Payload items to be written to AICache:")
    for idx, item in enumerate(cache_payload["items"]):
         print(f"  Item {idx}: cgst_rate={item.get('cgst_rate')} sgst_rate={item.get('sgst_rate')} igst_rate={item.get('igst_rate')}")
    print("Raw extraction items to be written to AICache:")
    for idx, item in enumerate(cache_payload["_raw_extraction"]["items"]):
         print(f"  Item {idx}: cgst_rate={item.get('cgst_rate')} sgst_rate={item.get('sgst_rate')} igst_rate={item.get('igst_rate')}")

    # ── SNAPSHOT 6 ──
    print("\n" + "="*40 + "\nSNAPSHOT 6: IMMEDIATELY AFTER READING AICache\n" + "="*40)
    # Simulate DB write and read using a temp key or using memory
    serialized_payload = json.dumps(cache_payload)
    read_payload = json.loads(serialized_payload)
    print("Payload items read from AICache:")
    for idx, item in enumerate(read_payload["items"]):
         print(f"  Item {idx}: cgst_rate={item.get('cgst_rate')} sgst_rate={item.get('sgst_rate')} igst_rate={item.get('igst_rate')}")
    print("Raw extraction items read from AICache:")
    for idx, item in enumerate(read_payload["_raw_extraction"]["items"]):
         print(f"  Item {idx}: cgst_rate={item.get('cgst_rate')} sgst_rate={item.get('sgst_rate')} igst_rate={item.get('igst_rate')}")

    # ── SNAPSHOT 7 ──
    print("\n" + "="*40 + "\nSNAPSHOT 7: IMMEDIATELY BEFORE normalize.get_normalized_items()\n" + "="*40)
    # Input to normalize.get_normalized_items() is `invoice`
    invoice_input = read_payload
    print("Line items inside invoice dict before calling normalize functions:")
    for idx, item in enumerate(invoice_input["items"]):
         gst_rate = float(item.get('gst_rate') or 0.0)
         print(f"  Item {idx}: desc='{item.get('description')}' | cgst_rate={item.get('cgst_rate')} | sgst_rate={item.get('sgst_rate')} | igst_rate={item.get('igst_rate')} | gst_rate={gst_rate}")

    # Run normalizer
    print("\nRunning get_normalized_items() output:")
    normalized_items = get_normalized_items(invoice_input, layout_type="Layout C")
    for idx, item in enumerate(normalized_items):
         print(f"  Item {idx}: desc='{item.get('description')}' | cgst_rate={item.get('cgst_rate')} | sgst_rate={item.get('sgst_rate')} | igst_rate={item.get('igst_rate')} | computed_gst_rate={item.get('computed_gst_rate')}")

if __name__ == '__main__':
    main()
