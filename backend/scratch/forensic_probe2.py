"""
Forensic DB probe part 2: Find the specific invoice with 25% discount
and trace the exact data divergence.
Run with: python manage.py shell --command="exec(open('scratch/forensic_probe2.py').read())"
"""
import json
from pending_purchases.models import PendingPurchase
from ocr_pipeline.models import InvoiceTempOCR

print("=== FORENSIC PROBE 2: Find discount=25% invoice ===\n")

# Scan ALL PENDING purchases for items with discount
all_pps = PendingPurchase.objects.filter(pending_purchase_status='PENDING').order_by('-updated_at')
print(f"Total PENDING PPs: {all_pps.count()}")

discount_pps = []
for pp in all_pps:
    ext = pp.extraction_payload or {}
    # Get items from various locations
    items = ext.get('items', [])
    if not items and ext.get('assembled_exports'):
        items = (ext['assembled_exports'][0] or {}).get('items', [])
    if not items and ext.get('sections', {}).get('items'):
        items = ext['sections']['items']
    
    for item in items:
        dp = item.get('discount_percent', 0) or 0
        da = item.get('discount_amount', 0) or 0
        try:
            dp = float(dp)
            da = float(da)
        except:
            dp = da = 0
        if dp > 0 or da > 0:
            discount_pps.append((pp, items, item))
            break

print(f"PPs with discount items: {len(discount_pps)}")

for pp, items, item0 in discount_pps:
    ext = pp.extraction_payload or {}
    audit = ext.get('gst_audit_trail', {})
    print(f"\n{'='*60}")
    print(f"[PP] id={pp.id}  invoice={pp.invoice_number}")
    print(f"  source_scan_row_id={pp.source_scan_row_id}")
    print(f"  PP.extraction_payload items count: {len(items)}")
    print(f"\n  [ITEM WITH DISCOUNT]")
    print(f"    description: {item0.get('description', item0.get('item_name', '?'))}")
    print(f"    qty: {item0.get('qty', item0.get('quantity', '?'))}")
    print(f"    rate: {item0.get('rate', item0.get('unit_price', '?'))}")
    print(f"    discount_percent: {item0.get('discount_percent', '<<MISSING>>')}")
    print(f"    discount_amount: {item0.get('discount_amount', '<<MISSING>>')}")
    print(f"    taxable_value: {item0.get('taxable_value', '<<MISSING>>')}")
    print(f"    amount: {item0.get('amount', '<<MISSING>>')}")
    gst_rate_val = item0.get('gst_rate') or item0.get('computed_gst_rate', '<<MISSING>>')
    print(f"    gst_rate: {gst_rate_val}")
    cgst_r = item0.get('cgst_rate', '<<MISSING>>')
    sgst_r = item0.get('sgst_rate', '<<MISSING>>')
    print(f"    cgst_rate: {cgst_r}  sgst_rate: {sgst_r}")
    print(f"    ALL ITEM KEYS: {list(item0.keys())}")
    
    print(f"\n  [PP GST AUDIT TRAIL]")
    print(f"    present: {bool(audit)}")
    print(f"    taxable_value: {audit.get('taxable_value', '<<MISSING>>')}")
    print(f"    expected_tax_values: {audit.get('expected_tax_values')}")
    print(f"    extracted_tax_values: {audit.get('extracted_tax_values')}")
    
    # Now check the STAGING record
    staging = InvoiceTempOCR.objects.filter(id=pp.source_scan_row_id).first()
    if staging:
        s_ext = staging.extracted_data or {}
        s_audit = s_ext.get('gst_audit_trail', {})
        s_items = s_ext.get('items', [])
        if not s_items and s_ext.get('assembled_exports'):
            s_items = (s_ext['assembled_exports'][0] or {}).get('items', [])
        
        print(f"\n  [STAGING InvoiceTempOCR id={staging.id}]")
        print(f"    validation_status: {staging.validation_status}")
        print(f"    processed: {staging.processed}")
        print(f"    status: {staging.status}")
        print(f"    gst_audit_trail taxable_value: {s_audit.get('taxable_value', '<<MISSING>>')}")
        print(f"    expected_tax_values: {s_audit.get('expected_tax_values')}")
        if s_items:
            si0 = s_items[0]
            print(f"\n  [STAGING Item[0]]")
            print(f"    discount_percent: {si0.get('discount_percent', '<<MISSING>>')}")
            print(f"    discount_amount: {si0.get('discount_amount', '<<MISSING>>')}")
            print(f"    taxable_value: {si0.get('taxable_value', '<<MISSING>>')}")
            print(f"    qty: {si0.get('qty', '?')}  rate: {si0.get('rate', '?')}")
        
        # DIVERGENCE POINT
        pp_audit_tv = audit.get('taxable_value')
        s_audit_tv = s_audit.get('taxable_value')
        pp_item0_dp = item0.get('discount_percent', 0)
        s_item0_dp = s_items[0].get('discount_percent', 0) if s_items else 'NO ITEMS'
        
        print(f"\n  [DIVERGENCE CHECK]")
        print(f"    PP.extraction_payload audit taxable_value: {pp_audit_tv}")
        print(f"    Staging.extracted_data audit taxable_value: {s_audit_tv}")
        print(f"    PP item[0] discount_percent: {pp_item0_dp}")
        print(f"    Staging item[0] discount_percent: {s_item0_dp}")
        
        if pp_audit_tv != s_audit_tv:
            print(f"    <<< AUDIT TRAIL DIVERGES: PP={pp_audit_tv} vs STAGING={s_audit_tv} >>>")
        
        pp_items_json = json.dumps(items, sort_keys=True, default=str)
        s_items_json = json.dumps(s_items, sort_keys=True, default=str)
        if pp_items_json != s_items_json:
            print(f"    <<< ITEMS DIVERGE BETWEEN PP AND STAGING >>>")
            # Show diffs for first item
            if items and s_items:
                for k in set(list(items[0].keys()) + list(s_items[0].keys())):
                    pv = items[0].get(k, '<<MISSING>>')
                    sv = s_items[0].get(k, '<<MISSING>>')
                    if pv != sv:
                        print(f"      KEY '{k}': PP={pv!r}  STAGING={sv!r}")
        else:
            print(f"    Items data IS IDENTICAL between PP and Staging")
    else:
        print(f"\n  [STAGING NOT FOUND] source_scan_row_id={pp.source_scan_row_id}")

print("\n=== PROBE 2 COMPLETE ===")
