import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from pending_purchases.models import PendingPurchase
from ocr_pipeline.models import InvoiceTempOCR

# The screenshot shows these invoice numbers: VMT25-26/1A7, UMT25-26/079, UMT25-26/091, UMT25-26/019, UMT25-26/251
# Let's find records where vendor_name is empty/null
pps = PendingPurchase.objects.filter(vendor_name__isnull=True) | PendingPurchase.objects.filter(vendor_name='') | PendingPurchase.objects.filter(vendor_name='-') | PendingPurchase.objects.filter(vendor_name='—')
pps = pps.order_by('-created_at')[:10]

print(f"Records with empty/null vendor_name: {pps.count()}")
for pp in pps:
    print('=== PendingPurchase ID:', pp.id)
    print('  vendor_name (DB):', repr(pp.vendor_name))
    print('  vendor_gstin (DB):', repr(pp.vendor_gstin))
    print('  invoice_number:', repr(pp.invoice_number))
    print('  vendor_status:', repr(pp.vendor_status))
    print('  voucher_status:', repr(pp.voucher_status))
    
    ext = pp.extraction_payload or {}
    print('  extraction_payload top-level keys:', list(ext.keys())[:25])
    
    # Check all the keys for vendor-like names
    vendor_keys = [k for k in ext.keys() if 'vendor' in k.lower() or 'supplier' in k.lower() or 'name' in k.lower() or 'party' in k.lower()]
    print('  Vendor-related top-level keys:', vendor_keys)
    for k in vendor_keys:
        print(f'    {k}: {repr(ext.get(k))[:100]}')
    
    # Check bill_from
    print('  bill_from:', repr(ext.get('bill_from', ''))[:100])
    
    staging = InvoiceTempOCR.objects.filter(id=pp.source_scan_row_id).first()
    if staging:
        s_ext = staging.extracted_data or {}
        print('  STAGING ext keys:', list(s_ext.keys())[:25])
        s_vendor_keys = [k for k in s_ext.keys() if 'vendor' in k.lower() or 'supplier' in k.lower() or 'name' in k.lower() or 'party' in k.lower()]
        print('  STAGING vendor-related keys:', s_vendor_keys)
        for k in s_vendor_keys:
            print(f'    STAGING {k}: {repr(s_ext.get(k))[:100]}')
        print('  STAGING bill_from:', repr(s_ext.get('bill_from', ''))[:100])
    else:
        print('  STAGING: NOT FOUND for id=', pp.source_scan_row_id)
    print()

print("=== Also check by invoice numbers from screenshot ===")
inv_nos = ['VMT25-26/1A7', 'UMT25-26/079', 'UMT25-26/091', 'UMT25-26/019', 'UMT25-26/251']
for inv in inv_nos:
    pp = PendingPurchase.objects.filter(invoice_number__iexact=inv).first()
    if pp:
        print(f"Found: inv={inv} vendor_name={repr(pp.vendor_name)} ext_keys={list((pp.extraction_payload or {}).keys())[:10]}")
        ext = pp.extraction_payload or {}
        # Print full bill_from if it exists
        if ext.get('bill_from'):
            print(f"  bill_from: {repr(ext.get('bill_from'))[:200]}")
    else:
        print(f"NOT FOUND: {inv}")
