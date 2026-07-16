"""
Forensic Probe 4: Deep dive into staging record 1009231 (most recently accessed GST_MISMATCH).
Trace the EXACT data at each layer.
Run with: python manage.py shell --command="exec(open('scratch/forensic_probe4.py').read())"
"""
import json
from pending_purchases.models import PendingPurchase
from ocr_pipeline.models import InvoiceTempOCR

TARGET_IDS = [1012638, 1012639, 1012649]

print("=== FORENSIC PROBE 4: Deep dive into specific staging records ===\n")

for staging_id in TARGET_IDS:
    staging = InvoiceTempOCR.objects.filter(id=staging_id).first()
    if not staging:
        print(f"[STAGING {staging_id}] NOT FOUND")
        continue
    
    print(f"\n{'='*70}")
    print(f"[STAGING {staging_id}] invoice={staging.supplier_invoice_no}")
    print(f"  validation_status: {staging.validation_status}")
    print(f"  processed: {staging.processed}")
    print(f"  status: {staging.status}")
    
    ext = staging.extracted_data or {}
    audit = ext.get('gst_audit_trail', {})
    
    # --- GST AUDIT TRAIL ---
    print(f"\n  [GST AUDIT TRAIL in InvoiceTempOCR.extracted_data]")
    if audit:
        print(f"    validation_status: {audit.get('validation_status')}")
        print(f"    taxable_value: {audit.get('taxable_value')}")
        print(f"    gst_rate: {audit.get('gst_rate')}")
        exp_tv = audit.get('expected_tax_values', {})
        print(f"    expected_tax_values: {exp_tv}")
        ext_tv = audit.get('extracted_tax_values', {})
        print(f"    extracted_tax_values: {ext_tv}")
        print(f"    difference_amount: {audit.get('difference_amount')}")
    else:
        print("    [NO AUDIT TRAIL FOUND]")
    
    # --- ITEMS ---
    items = ext.get('items', [])
    if not items and ext.get('assembled_exports'):
        items = (ext['assembled_exports'][0] or {}).get('items', [])
    if not items and ext.get('sections', {}).get('items'):
        items = ext['sections']['items']
    
    print(f"\n  [ITEMS in InvoiceTempOCR.extracted_data] count={len(items)}")
    for i, itm in enumerate(items):
        qty = itm.get('qty', itm.get('quantity', 0))
        rate = itm.get('rate', itm.get('unit_price', 0))
        dp = itm.get('discount_percent', '<<MISSING>>')
        da = itm.get('discount_amount', '<<MISSING>>')
        tv = itm.get('taxable_value', '<<MISSING>>')
        amt = itm.get('amount', '<<MISSING>>')
        gst_r = itm.get('gst_rate') or itm.get('computed_gst_rate') or '<<MISSING>>'
        cgst_r = itm.get('cgst_rate', '<<MISSING>>')
        sgst_r = itm.get('sgst_rate', '<<MISSING>>')
        cgst = itm.get('cgst_amount') or itm.get('cgst')
        sgst = itm.get('sgst_amount') or itm.get('sgst')
        
        print(f"\n  Item[{i}] desc: {itm.get('description', itm.get('item_name', '?'))}")
        print(f"    qty={qty}  rate={rate}")
        print(f"    discount_percent={dp}  discount_amount={da}")
        print(f"    taxable_value={tv}  amount={amt}")
        print(f"    gst_rate={gst_r}  cgst_rate={cgst_r}  sgst_rate={sgst_r}")
        print(f"    cgst={cgst}  sgst={sgst}")
        
        # Simulate what GstCorrectionModal.calculateItemTaxableValue would compute
        try:
            qty_f = float(qty) if qty else 0
            rate_f = float(rate) if rate else 0
            dp_f = float(dp) if (dp is not None and dp != '<<MISSING>>') else 0
            da_f = float(da) if (da is not None and da != '<<MISSING>>') else 0
            tv_f = float(tv) if (tv != '<<MISSING>>' and tv is not None) else None
            
            gross = qty_f * rate_f
            print(f"\n    [REACT SIMULATION] calculateItemTaxableValue:")
            print(f"    gross = qty({qty_f}) * rate({rate_f}) = {gross:.2f}")
            print(f"    getItemDiscountPct -> discPct = {dp_f}")
            print(f"    getItemDiscountAmt -> discAmt = {da_f}")
            
            if dp_f > 0:
                calc_tv = round(gross * (1 - dp_f/100), 2)
                print(f"    [RULE 1 - discPct branch] taxable = {gross:.2f} * (1 - {dp_f}/100) = {calc_tv:.2f}")
                discount_display = f"{dp_f}%"
            elif da_f > 0:
                calc_tv = round(gross - da_f, 2)
                print(f"    [RULE 1 - discAmt branch] taxable = {gross:.2f} - {da_f} = {calc_tv:.2f}")
                discount_display = f"Rs {da_f:.2f}"
            elif tv_f is not None and tv_f != 0:
                calc_tv = tv_f
                print(f"    [RULE 2 - trust stored taxable_value] taxable = {calc_tv:.2f}")
                discount_display = "-"
            elif amt != '<<MISSING>>' and amt:
                calc_tv = float(amt)
                print(f"    [RULE 3 - use amount field] taxable = {calc_tv:.2f}")
                discount_display = "-"
            else:
                calc_tv = round(gross, 2)
                print(f"    [RULE 4 - fallback to gross] taxable = {calc_tv:.2f}")
                discount_display = "-"
            
            print(f"    RENDERED discount = '{discount_display}'")
            print(f"    RENDERED taxable_value = {calc_tv:.2f}")
            
            # Calculate expected GST
            gst_rate_f = 0
            if gst_r != '<<MISSING>>' and gst_r:
                try:
                    gst_rate_f = float(str(gst_r).replace('%',''))
                except: pass
            if gst_rate_f == 0 and cgst_r != '<<MISSING>>':
                try:
                    gst_rate_f = float(cgst_r or 0) * 2  # cgst+sgst
                except: pass
            
            if gst_rate_f > 0:
                exp_gst = round(calc_tv * gst_rate_f / 100, 2)
                print(f"    RENDERED expected_gst = {calc_tv:.2f} * {gst_rate_f}% = {exp_gst:.2f}")
        except Exception as e:
            print(f"    [SIMULATION ERROR] {e}")
    
    # --- Linked PendingPurchase ---
    pp = PendingPurchase.objects.filter(source_scan_row_id=staging_id).first()
    if pp:
        print(f"\n  [LINKED PendingPurchase] id={pp.id} invoice={pp.invoice_number}")
        pp_ext = pp.extraction_payload or {}
        pp_audit = pp_ext.get('gst_audit_trail', {})
        print(f"    PP.extraction_payload audit taxable_value: {pp_audit.get('taxable_value') if isinstance(pp_audit, dict) else 'N/A'}")
        
        pp_items = pp_ext.get('items', [])
        if not pp_items and pp_ext.get('assembled_exports'):
            pp_items = (pp_ext['assembled_exports'][0] or {}).get('items', [])
        
        print(f"    PP items count: {len(pp_items)}")
        if pp_items:
            pi0 = pp_items[0]
            print(f"    PP Item[0] discount_percent: {pi0.get('discount_percent', '<<MISSING>>')}")
            print(f"    PP Item[0] taxable_value: {pi0.get('taxable_value', '<<MISSING>>')}")
        
        # DIVERGENCE ANALYSIS
        print(f"\n  [DIVERGENCE ANALYSIS]")
        print(f"    staging.extracted_data.gst_audit_trail == pp.extraction_payload.gst_audit_trail: {audit == pp_audit}")
        staging_items_json = json.dumps(items, sort_keys=True, default=str)
        pp_items_json = json.dumps(pp_items, sort_keys=True, default=str)
        print(f"    items DATA MATCHES: {staging_items_json == pp_items_json}")
        
        if items and pp_items and staging_items_json != pp_items_json:
            print(f"    <<< DIVERGENCE IN ITEMS DETECTED >>>")
            for k in set(list(items[0].keys()) + list(pp_items[0].keys())):
                sv = items[0].get(k, '<<MISSING>>')
                pv = pp_items[0].get(k, '<<MISSING>>')
                if sv != pv:
                    print(f"      KEY '{k}': STAGING={sv!r}  PP={pv!r}")
    else:
        print(f"\n  [NO LINKED PendingPurchase for staging_id={staging_id}]")
        # This means dialog is from SmartInvoiceUploadModal NOT PendingPurchases

print("\n\n=== PROBE 4 COMPLETE ===")
