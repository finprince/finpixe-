"""
Forensic DB probe: compare PendingPurchase.extraction_payload vs InvoiceTempOCR.extracted_data
for all GST-mismatch entries to find the point of data divergence.
Run with: python manage.py shell < scratch/forensic_db_probe.py
"""
import json
from pending_purchases.models import PendingPurchase
from ocr_pipeline.models import InvoiceTempOCR

# Get all PENDING purchases
all_pps = PendingPurchase.objects.filter(pending_purchase_status='PENDING').order_by('-updated_at')[:30]

mismatch_pps = []
for pp in all_pps:
    ext = pp.extraction_payload or {}
    audit = ext.get('gst_audit_trail', {})
    if isinstance(audit, dict) and audit.get('validation_status') == 'FAIL':
        mismatch_pps.append(pp)

print(f"=== FORENSIC DB PROBE ===")
print(f"Total PENDING PPs examined: {all_pps.count()}")
print(f"GST MISMATCH PPs found: {len(mismatch_pps)}")

for pp in mismatch_pps[:5]:
    print(f"\n{'='*60}")
    print(f"[PENDING PURCHASE] id={pp.id}  invoice={pp.invoice_number}")
    print(f"  source_scan_row_id={pp.source_scan_row_id}")
    print(f"  updated_at={pp.updated_at}")

    # --- PP extraction_payload analysis ---
    pp_ext = pp.extraction_payload or {}
    pp_audit = pp_ext.get('gst_audit_trail', {})
    pp_items = (
        pp_ext.get('items') or
        (pp_ext.get('sections') or {}).get('items') or
        (pp_ext.get('assembled_exports') or [{}])[0].get('items') if pp_ext.get('assembled_exports') else None or
        []
    )
    if not pp_items:
        pp_items = pp_ext.get('items', [])

    print(f"\n  [PP.extraction_payload]")
    print(f"    gst_audit_trail present: {bool(pp_audit)}")
    print(f"    taxable_value in audit: {pp_audit.get('taxable_value')}")
    print(f"    expected_tax_values: {pp_audit.get('expected_tax_values')}")
    print(f"    extracted_tax_values: {pp_audit.get('extracted_tax_values')}")
    print(f"    items count: {len(pp_items)}")
    if pp_items:
        item0 = pp_items[0]
        print(f"    Item[0] keys: {list(item0.keys())[:20]}")
        print(f"    Item[0] description: {item0.get('description', item0.get('item_name', '?'))}")
        print(f"    Item[0] qty: {item0.get('qty', item0.get('quantity', '?'))}")
        print(f"    Item[0] rate: {item0.get('rate', item0.get('unit_price', '?'))}")
        print(f"    Item[0] discount_percent: {item0.get('discount_percent', '<<MISSING>>')}")
        print(f"    Item[0] discount_pct: {item0.get('discount_pct', '<<MISSING>>')}")
        print(f"    Item[0] discount_amount: {item0.get('discount_amount', '<<MISSING>>')}")
        print(f"    Item[0] discount (raw): {item0.get('discount', '<<MISSING>>')}")
        print(f"    Item[0] taxable_value: {item0.get('taxable_value', '<<MISSING>>')}")
        print(f"    Item[0] amount: {item0.get('amount', '<<MISSING>>')}")
        print(f"    Item[0] gst_rate: {item0.get('gst_rate', '<<MISSING>>')}")
        print(f"    Item[0] computed_gst_rate: {item0.get('computed_gst_rate', '<<MISSING>>')}")
        print(f"    Item[0] cgst_rate: {item0.get('cgst_rate', '<<MISSING>>')}")
        print(f"    Item[0] sgst_rate: {item0.get('sgst_rate', '<<MISSING>>')}")
        print(f"    Item[0] cgst: {item0.get('cgst', '<<MISSING>>')}")
        print(f"    Item[0] sgst: {item0.get('sgst', '<<MISSING>>')}")

    # --- Staging record analysis ---
    staging = InvoiceTempOCR.objects.filter(id=pp.source_scan_row_id).first()
    if not staging:
        print(f"\n  [STAGING] NOT FOUND for id={pp.source_scan_row_id}")
        continue

    s_ext = staging.extracted_data or {}
    s_audit = s_ext.get('gst_audit_trail', {})
    s_items = s_ext.get('items', [])
    if not s_items and s_ext.get('assembled_exports'):
        s_items = (s_ext['assembled_exports'][0] or {}).get('items', [])

    print(f"\n  [STAGING InvoiceTempOCR] id={staging.id}")
    print(f"    validation_status: {staging.validation_status}")
    print(f"    processed: {staging.processed}")
    print(f"    gst_audit_trail present: {bool(s_audit)}")
    print(f"    taxable_value in audit: {s_audit.get('taxable_value')}")
    print(f"    expected_tax_values: {s_audit.get('expected_tax_values')}")
    print(f"    items count: {len(s_items)}")
    if s_items:
        si0 = s_items[0]
        print(f"    Item[0] discount_percent: {si0.get('discount_percent', '<<MISSING>>')}")
        print(f"    Item[0] discount_amount: {si0.get('discount_amount', '<<MISSING>>')}")
        print(f"    Item[0] taxable_value: {si0.get('taxable_value', '<<MISSING>>')}")
        print(f"    Item[0] qty: {si0.get('qty', '?')}  rate: {si0.get('rate', '?')}")

    # --- Divergence check ---
    print(f"\n  [DIVERGENCE CHECK]")
    pp_taxable = pp_audit.get('taxable_value', 'MISSING')
    s_taxable = s_audit.get('taxable_value', 'MISSING')
    print(f"    PP audit taxable_value: {pp_taxable}")
    print(f"    Staging audit taxable_value: {s_taxable}")
    print(f"    ARE EQUAL: {pp_taxable == s_taxable}")

    # Check if pp.extraction_payload and staging.extracted_data differ in items
    pp_audit_json = json.dumps(pp_audit, sort_keys=True, default=str)
    s_audit_json = json.dumps(s_audit, sort_keys=True, default=str)
    print(f"    gst_audit_trail MATCHES: {pp_audit_json == s_audit_json}")
    
    if pp_items and s_items:
        pp_i0_json = json.dumps(pp_items[0], sort_keys=True, default=str)
        s_i0_json = json.dumps(s_items[0], sort_keys=True, default=str)
        print(f"    Item[0] MATCHES: {pp_i0_json == s_i0_json}")
        if pp_i0_json != s_i0_json:
            print(f"    <<< ITEM DATA DIVERGES >>>")
            # Show diff
            pp_i0 = pp_items[0]
            s_i0 = s_items[0]
            for k in set(list(pp_i0.keys()) + list(s_i0.keys())):
                pv = pp_i0.get(k, '<<MISSING>>')
                sv = s_i0.get(k, '<<MISSING>>')
                if pv != sv:
                    print(f"      KEY '{k}': PP={pv!r}  STAGING={sv!r}")

print("\n=== PROBE COMPLETE ===")
