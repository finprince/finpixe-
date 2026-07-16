import os
import sys
import django
import json
import base64

def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    django.setup()

    from ocr_pipeline.isolated_ocr_service import run_isolated_page_extraction
    from mistralai.client import Mistral
    from mistralai.extra import response_format_from_pydantic_model
    from core.providers.mistral_structured_provider import MistralStructuredInvoiceSchema

    pdf_path = r"c:\108\AI-accounting-0.03\backend\media\bulk_pipeline\ocr\2eda0ac6-6af2-493e-8792-bc973fe946b7\ec956bb9-8170-4462-b723-c6a65ce6bc6e\c2ab2f6b5da0b8f9d2e1a86cb4b88c1549439c1bdbe3df267d59c689f529675a_IMG_20260406_0003.pdf"

    print("Locating correct page index...")
    target_text = "EZZI INDUSTRIAL STORES"
    matching_idx = None
    matching_iso_res = None

    # Let's search pages 10 to 16
    for idx in range(10, 18):
        try:
            print(f"Extracting page index {idx}...")
            iso_res = run_isolated_page_extraction(pdf_path, idx)
            text = iso_res.get("text", "")
            if target_text in text and "EIS/25-26/1014" in text:
                print(f"FOUND MATCH at page index {idx}!")
                matching_idx = idx
                matching_iso_res = iso_res
                break
        except Exception as e:
            print(f"Error on page index {idx}: {e}")

    if matching_idx is None:
        print("Could not find matching page for invoice EIS/25-26/1014")
        sys.exit(1)

    # Build the prompt
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

    prompt_text = f"{base_prompt}\n\n### [PAGE {matching_idx+1} OCR DATA]\n{matching_iso_res['text']}"

    img_bytes = matching_iso_res["image_bytes"]
    file_b64 = base64.b64encode(img_bytes).decode('utf-8')

    document_payload = {
        "type": "image_url",
        "image_url": f"data:image/jpeg;base64,{file_b64}"
    }

    print("Initializing Mistral client...")
    api_key = os.getenv("MISTRAL_API_KEY")
    client = Mistral(api_key=api_key)

    print("Calling Mistral OCR cloud API...")
    response = client.ocr.process(
        model="mistral-ocr-latest",
        document=document_payload,
        document_annotation_format=response_format_from_pydantic_model(MistralStructuredInvoiceSchema),
        document_annotation_prompt=prompt_text
    )

    print("\nMISTRAL RAW API RESPONSE:")
    print(response.model_dump_json(indent=2))

if __name__ == '__main__':
    main()
