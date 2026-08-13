import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from pending_purchases.models import PendingPurchase
from ocr_pipeline.models import InvoiceTempOCR

pps = PendingPurchase.objects.all().order_by('-created_at')[:5]
for pp in pps:
    print('=== PendingPurchase ID:', pp.id)
    print('  vendor_name (DB):', repr(pp.vendor_name))
    print('  vendor_gstin (DB):', repr(pp.vendor_gstin))
    print('  invoice_number:', repr(pp.invoice_number))
    print('  vendor_status:', repr(pp.vendor_status))
    print('  voucher_status:', repr(pp.voucher_status))
    
    ext = pp.extraction_payload or {}
    print('  extraction_payload top-level keys:', list(ext.keys())[:20])
    sections = ext.get('sections', {})
    supplier = sections.get('supplier_details', {})
    header = ext.get('header', {})
    print('  sections keys:', list(sections.keys()))
    print('  supplier_details keys:', list(supplier.keys())[:15])
    print('  header keys:', list(header.keys())[:15])
    print('  supplier.vendor_name:', repr(supplier.get('vendor_name')))
    print('  supplier.name:', repr(supplier.get('name')))
    print('  header.vendor_name:', repr(header.get('vendor_name')))
    print('  ext.vendor_name:', repr(ext.get('vendor_name')))
    
    staging = InvoiceTempOCR.objects.filter(id=pp.source_scan_row_id).first()
    if staging:
        s_ext = staging.extracted_data or {}
        s_sections = s_ext.get('sections', {})
        s_supplier = s_sections.get('supplier_details', {})
        s_header = s_ext.get('header', {})
        print('  --- STAGING ID:', staging.id)
        print('  STAGING ext top-keys:', list(s_ext.keys())[:20])
        print('  STAGING sections keys:', list(s_sections.keys()))
        print('  STAGING supplier keys:', list(s_supplier.keys())[:15])
        print('  STAGING header keys:', list(s_header.keys())[:15])
        print('  STAGING supplier.vendor_name:', repr(s_supplier.get('vendor_name')))
        print('  STAGING supplier.name:', repr(s_supplier.get('name')))
        print('  STAGING header.vendor_name:', repr(s_header.get('vendor_name')))
        print('  STAGING ext.vendor_name:', repr(s_ext.get('vendor_name')))
    else:
        print('  STAGING: NOT FOUND for id=', pp.source_scan_row_id)
    print()

print("=== DONE ===")
