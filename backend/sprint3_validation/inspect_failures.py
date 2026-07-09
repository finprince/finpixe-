import os, sys, json
sys.path.insert(0,".")
os.environ.setdefault("DJANGO_SETTINGS_MODULE","backend.settings")
import django; django.setup()
from ocr_pipeline.models import InvoiceTempOCR

failed_ids = [1008380, 1008386, 1008387]
for fid in failed_ids:
    print("=" * 70)
    print(f"Inspection for ID {fid}")
    r = InvoiceTempOCR.objects.get(id=fid)
    data = r.extracted_data or {}
    print(f"Status: {r.status} | Validation: {r.validation_status}")
    print(f"Supplier Invoice No: {r.supplier_invoice_no}")
    print("Header fields in extracted_data:")
    print("  total_taxable_value:", data.get("total_taxable_value"))
    print("  total_cgst:         ", data.get("total_cgst"))
    print("  total_sgst:         ", data.get("total_sgst"))
    print("  total_igst:         ", data.get("total_igst"))
    print("  total_invoice_value:", data.get("total_invoice_value"))
    print("  round_off:          ", data.get("round_off"))
    print("Items:")
    items = data.get("items", [])
    for i, it in enumerate(items):
        print(f"  [{i}] desc: {repr(it.get('description') or it.get('item_name'))[:60]}")
        print(f"      taxable: {it.get('taxable_value')} | qty: {it.get('qty')} | rate: {it.get('rate')}")
        print(f"      cgst: {it.get('cgst')} | sgst: {it.get('sgst')} | igst: {it.get('igst')} | total: {it.get('total_amount')}")
    print("Raw OCR Text snippet:")
    txt = str(data.get("_pdf_ocr_text") or data.get("_raw_text") or "")[:800]
    print(txt.encode('ascii', errors='replace').decode('ascii'))
