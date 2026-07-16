"""
Forensic Probe 3: Find the specific invoice showing:
  - Discount = "-"
  - Taxable Value = Rs 1,597.00
  - Expected GST = Rs 287.46

And trace the exact data path from DB -> API -> React prop -> rendered value.
Run with: python manage.py shell --command="exec(open('scratch/forensic_probe3.py').read())"
"""
import json
from pending_purchases.models import PendingPurchase
from ocr_pipeline.models import InvoiceTempOCR

print("=== FORENSIC PROBE 3: Track 1597 taxable value invoice ===\n")

# --- SCAN 1: All pending purchases with audit trail ---
all_pps = PendingPurchase.objects.filter(pending_purchase_status='PENDING').order_by('-updated_at')
print(f"Total PENDING PPs: {all_pps.count()}")

for pp in all_pps:
    ext = pp.extraction_payload or {}
    audit = ext.get('gst_audit_trail', {})
    if not isinstance(audit, dict):
        continue
    tv = audit.get('taxable_value', 0)
    try:
        tv = float(tv)
    except:
        tv = 0
    # Look for the ~1597 taxable value
    if 1500 < tv < 1700:
        print(f"\n[MATCH] PP id={pp.id} invoice={pp.invoice_number}")
        print(f"  taxable_value in audit: {tv}")
        print(f"  expected_tax_values: {audit.get('expected_tax_values')}")

# --- SCAN 2: All staging records with audit trail for GST mismatch ---
print("\n\n--- SCANNING ALL GST MISMATCH STAGING RECORDS ---")
mismatch_staging = InvoiceTempOCR.objects.filter(validation_status='PENDING_PURCHASE')
print(f"Total PENDING_PURCHASE staging: {mismatch_staging.count()}")

TARGET_TAXABLE = None  # will find

for s in mismatch_staging.order_by('-updated_at')[:50]:
    ext = s.extracted_data or {}
    audit = ext.get('gst_audit_trail', {})
    if not isinstance(audit, dict):
        continue
    if audit.get('validation_status') != 'FAIL':
        continue
    tv = audit.get('taxable_value', 0)
    try:
        tv = float(tv)
    except:
        tv = 0
    if 1500 < tv < 1700:
        print(f"\n[STAGING MATCH] id={s.id} invoice={s.supplier_invoice_no}")
        print(f"  taxable_value in audit: {tv}")
        print(f"  expected_tax_values: {audit.get('expected_tax_values')}")
        
        items = ext.get('items', [])
        if not items and ext.get('assembled_exports'):
            items = (ext['assembled_exports'][0] or {}).get('items', [])
        if not items and ext.get('sections', {}).get('items'):
            items = ext['sections']['items']
        
        print(f"  items count: {len(items)}")
        for i, itm in enumerate(items[:3]):
            print(f"  Item[{i}] desc: {itm.get('description', itm.get('item_name', '?'))}")
            print(f"  Item[{i}] qty: {itm.get('qty', '?')}  rate: {itm.get('rate', '?')}")
            print(f"  Item[{i}] discount_percent: {itm.get('discount_percent', '<<NONE>>')}")
            print(f"  Item[{i}] discount_amount: {itm.get('discount_amount', '<<NONE>>')}")
            print(f"  Item[{i}] taxable_value: {itm.get('taxable_value', '<<NONE>>')}")
            print(f"  Item[{i}] amount: {itm.get('amount', '<<NONE>>')}")
        TARGET_TAXABLE = s.id

# --- SCAN 3: Look for recently uploaded invoices with GST_MISMATCH status ---
print("\n\n--- SCANNING GST_MISMATCH STAGING RECORDS ---")
gst_mismatch_staging = InvoiceTempOCR.objects.filter(validation_status='GST_MISMATCH').order_by('-updated_at')[:20]
print(f"GST_MISMATCH staging found: {gst_mismatch_staging.count()}")

for s in gst_mismatch_staging:
    ext = s.extracted_data or {}
    audit = ext.get('gst_audit_trail', {})
    tv = audit.get('taxable_value', 0) if isinstance(audit, dict) else 0
    exp_gst = None
    if isinstance(audit, dict):
        ev = audit.get('expected_tax_values', {})
        exp_gst = ev.get('total_gst') if isinstance(ev, dict) else None
    
    items = ext.get('items', [])
    if not items and ext.get('assembled_exports'):
        items = (ext['assembled_exports'][0] or {}).get('items', [])
    
    disc_info = []
    for itm in items:
        dp = itm.get('discount_percent', 0) or 0
        da = itm.get('discount_amount', 0) or 0
        if dp or da:
            disc_info.append(f"pct={dp} amt={da}")

    print(f"\n[GST_MISMATCH] id={s.id} invoice={s.supplier_invoice_no}")
    print(f"  taxable_value: {tv}  expected_gst: {exp_gst}")
    print(f"  items: {len(items)}  discounts: {disc_info}")
    
    # Check linked PP
    pp = PendingPurchase.objects.filter(source_scan_row_id=s.id).first()
    if pp:
        pp_ext = pp.extraction_payload or {}
        pp_audit = pp_ext.get('gst_audit_trail', {})
        pp_tv = pp_audit.get('taxable_value', 'N/A') if isinstance(pp_audit, dict) else 'N/A'
        print(f"  PP.extraction_payload audit taxable_value: {pp_tv}")
        print(f"  PP audit == Staging audit: {pp_audit == audit}")

# --- SCAN 4: Check what SmartInvoiceUpload sees - scan ALL unresolved staging records ---
print("\n\n--- CHECKING ALL UNRESOLVED STAGING RECORDS ---")
unresolved = InvoiceTempOCR.objects.filter(
    validation_status__in=['GST_MISMATCH', 'NEED_TO_SAVE', 'PENDING_PURCHASE']
).order_by('-updated_at')[:30]
print(f"Unresolved staging: {unresolved.count()}")

for s in unresolved:
    ext = s.extracted_data or {}
    audit = ext.get('gst_audit_trail', {})
    if not isinstance(audit, dict):
        continue
    if audit.get('validation_status') != 'FAIL':
        continue
    tv = audit.get('taxable_value', 0)
    ev = audit.get('expected_tax_values', {}) or {}
    exp_gst = ev.get('total_gst', 0) if isinstance(ev, dict) else 0
    
    items = ext.get('items', [])
    if not items and ext.get('assembled_exports'):
        items = (ext['assembled_exports'][0] or {}).get('items', [])
    
    disc_items = [itm for itm in items if (itm.get('discount_percent', 0) or itm.get('discount_amount', 0))]
    
    try:
        tv_f = float(tv)
        exp_gst_f = float(exp_gst)
    except:
        tv_f = exp_gst_f = 0
    
    print(f"\n[FAIL AUDIT] Staging id={s.id} invoice={s.supplier_invoice_no} status={s.validation_status}")
    print(f"  taxable_value={tv_f:.2f}  expected_gst={exp_gst_f:.2f}")
    print(f"  items={len(items)}  discount_items={len(disc_items)}")
    
    if disc_items:
        di0 = disc_items[0]
        print(f"  Discount item[0]: dp={di0.get('discount_percent')} da={di0.get('discount_amount')}")
        print(f"  Discount item[0]: taxable_value={di0.get('taxable_value')} rate={di0.get('rate')} qty={di0.get('qty')}")
        
        # The report claims: 
        # Expected: discount=25%, taxable=1946.25, expected_gst=350.33
        # Actual UI: discount="-", taxable=1597.00, expected_gst=287.46
        # So taxable_value=1597.00 or 1946.25
        print(f"\n  >>> ANALYZING DIVERGENCE for this item <<<")
        qty = float(di0.get('qty') or 0)
        rate = float(di0.get('rate') or 0)
        disc_pct = float(di0.get('discount_percent') or 0)
        disc_amt = float(di0.get('discount_amount') or 0)
        taxable = float(di0.get('taxable_value') or 0)
        gross = qty * rate
        
        print(f"  qty={qty}  rate={rate}  gross={gross:.2f}")
        print(f"  discount_percent={disc_pct}  discount_amount={disc_amt}")
        print(f"  stored taxable_value={taxable:.2f}")
        
        if disc_pct > 0:
            calc_taxable = gross * (1 - disc_pct/100)
            print(f"  CALCULATED taxable (with {disc_pct}% disc) = {calc_taxable:.2f}")
        
        print(f"\n  What GstCorrectionModal would see:")
        print(f"  discPct = {disc_pct} (via discount_percent)")
        print(f"  discAmt = {disc_amt} (via discount_amount)")
        if disc_pct > 0:
            modal_taxable = round(gross * (1 - disc_pct/100), 2)
            print(f"  calculateItemTaxableValue = {modal_taxable:.2f} (using discPct branch)")
        elif disc_amt > 0:
            modal_taxable = round(gross - disc_amt, 2)
            print(f"  calculateItemTaxableValue = {modal_taxable:.2f} (using discAmt branch)")
        else:
            modal_taxable = taxable  # falls back to stored value
            print(f"  calculateItemTaxableValue = {modal_taxable:.2f} (fallback to stored taxable_value)")

print("\n=== PROBE 3 COMPLETE ===")
