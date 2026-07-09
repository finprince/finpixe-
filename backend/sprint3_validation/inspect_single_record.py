import os, sys, django, json
sys.path.insert(0,".")
os.environ.setdefault("DJANGO_SETTINGS_MODULE","backend.settings")
django.setup()
from ocr_pipeline.models import InvoiceTempOCR, InvoicePageResult

rid = 1008386
r = InvoiceTempOCR.objects.get(id=rid)
print(f"=== InvoiceTempOCR id={rid} ===")
print("File Path:", r.file_path)
print("Status:", r.status)
print("Supplier Invoice No:", r.supplier_invoice_no)
print("GSTIN:", r.gstin)
print("Extracted Data keys:", list((r.extracted_data or {}).keys()))
print("Extracted Data values:")
for k in ["invoice_no", "canonical_invoice_no", "vendor_name", "canonical_vendor_name", "total_taxable_value", "total_invoice_value", "item_status"]:
    print(f"  {k}: {r.extracted_data.get(k)}")

print("\n=== Sibling page results in DB ===")
pages = InvoicePageResult.objects.filter(record_id=rid).order_by('page_number')
for p in pages:
    print(f"Page {p.page_number} (id={p.id}):")
    cp = p.canonical_payload or {}
    print("  GSTIN:", cp.get('gstin'))
    print("  Invoice No:", cp.get('invoice_no'))
    print("  Vendor Name:", cp.get('vendor_name'))
    print("  Total Taxable Value:", cp.get('total_taxable_value'))
    print("  Total Invoice Value:", cp.get('total_invoice_value'))
