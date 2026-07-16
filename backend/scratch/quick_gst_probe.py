"""
Quick GST Data Lineage Probe — directly inspects finalized records for IMG_20260406_0003.pdf
"""
import os, sys, json
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import django; django.setup()
from ocr_pipeline.models import InvoiceTempOCR

def to_float(val):
    if val is None: return 0.0
    try:
        return float(str(val).replace(',','').replace('Rs','').replace('INR','').strip())
    except: return 0.0

TARGET_IDS = [1009294, 1009295, 1009283, 1009284]

print("=" * 100)
print("PHASE 0 — DATA LINEAGE: GST values at each stage")
print("=" * 100)

for rid in TARGET_IDS:
    r = InvoiceTempOCR.objects.filter(id=rid).first()
    if not r:
        continue
    d = r.extracted_data or {}
    ae_list = d.get('assembled_exports') or d.get('_pages_assembled') or []
    ae = ae_list[0] if ae_list else {}
    sec_root = d.get('sections') or {}
    sec_ae   = (ae.get('sections') or {}) if ae else {}
    sup_root = sec_root.get('supply_details') or {}
    sup_ae   = sec_ae.get('supply_details') or {}
    sup      = sup_ae or sup_root

    print(f"\n{'#'*100}")
    print(f"# Record {rid} | inv_no={r.supplier_invoice_no} | val_status={r.validation_status} | status={r.status}")
    print(f"{'#'*100}")

    # Stage 1: Root-level extracted_data
    print("\nSTAGE 1 — AI Raw JSON (extracted_data root keys):")
    for k in ['taxable_value','total_taxable_value','cgst','total_cgst','sgst','total_sgst',
              'igst','total_igst','cess','total_cess','invoice_total','total_invoice_value',
              'total_amount','discount','round_off']:
        v = d.get(k)
        if v is not None:
            print(f"  {k}: {v}")

    # Stage 2: assembled_exports root
    if ae:
        print("\nSTAGE 2 — Assembled Export (assembled_exports[0] root keys):")
        for k in ['taxable_value','total_taxable_value','cgst','total_cgst','sgst','total_sgst',
                  'igst','total_igst','cess','total_cess','invoice_total','total_invoice_value',
                  'total_amount','discount','round_off']:
            v = ae.get(k)
            if v is not None:
                print(f"  {k}: {v}")

    # Stage 3: supply_details
    print("\nSTAGE 3 — Supply Details (sections.supply_details):")
    for k in ['total_taxable_value','taxable_value','total_cgst','total_sgst','total_igst',
              'total_cess','total_invoice_value','invoice_total','discount','round_off','grand_total']:
        v = sup.get(k)
        if v is not None:
            print(f"  {k}: {v}")

    # Stage 4: GST Audit Trail
    gst = d.get('gst_audit_trail') or {}
    if gst:
        print("\nSTAGE 4 — GST Audit Trail (already computed by pipeline):")
        print(f"  validation_status : {gst.get('validation_status')}")
        print(f"  difference_amount : {gst.get('difference_amount')}")
        print(f"  taxable_value     : {gst.get('taxable_value')}")
        print(f"  gst_rate          : {gst.get('gst_rate')}")
        exp = gst.get('expected_tax_values') or {}
        ext = gst.get('extracted_tax_values') or {}
        print(f"  EXPECTED (computed from items):")
        print(f"    cgst={exp.get('cgst')}  sgst={exp.get('sgst')}  igst={exp.get('igst')}  cess={exp.get('cess')}  total={exp.get('total')}")
        print(f"  EXTRACTED (from AI JSON):")
        print(f"    cgst={ext.get('cgst')}  sgst={ext.get('sgst')}  igst={ext.get('igst')}  cess={ext.get('cess')}  total={ext.get('total')}")

        diff = to_float(gst.get('difference_amount'))
        if diff > 1.0:
            print(f"\n  *** GST MISMATCH DETECTED: difference={diff:.2f} > tolerance=1.0 ***")
        else:
            print(f"\n  *** GST PASS: difference={diff:.2f} <= 1.0 ***")
    else:
        print("\nSTAGE 4 — GST Audit Trail: [NOT FOUND in extracted_data]")

    # Stage 5: Item-level breakdown
    items = d.get('items') or ae.get('items') or []
    if not items and ae:
        ae_sec = ae.get('sections') or {}
        items = ae_sec.get('items') or []
    print(f"\nSTAGE 5 — Item-Level Tax Breakdown ({len(items)} items):")
    sum_tx=0.0; sum_cg=0.0; sum_sg=0.0; sum_ig=0.0; sum_cs=0.0
    for i, item in enumerate(items):
        tx   = to_float(item.get('taxable_value') or item.get('taxable'))
        cg   = to_float(item.get('cgst_amount') or item.get('cgst'))
        sg   = to_float(item.get('sgst_amount') or item.get('sgst'))
        ig   = to_float(item.get('igst_amount') or item.get('igst'))
        cs   = to_float(item.get('cess_amount') or item.get('cess'))
        rate = to_float(item.get('gst_rate') or item.get('tax_rate'))
        desc = str(item.get('description') or item.get('item_name') or '')[:35]
        print(f"  {i+1:02d}: {desc!r:<37} tx={tx:9.2f} gst={rate}%  cgst={cg:7.2f}  sgst={sg:7.2f}  igst={ig:7.2f}  cess={cs:5.2f}")
        sum_tx+=tx; sum_cg+=cg; sum_sg+=sg; sum_ig+=ig; sum_cs+=cs

    print(f"  {'ITEM SUM':<39} tx={sum_tx:9.2f}         cgst={sum_cg:7.2f}  sgst={sum_sg:7.2f}  igst={sum_ig:7.2f}  cess={sum_cs:5.2f}")

    # calculate_item_taxable_value comparison
    print("\nSTAGE 6 — calculate_item_taxable_value re-computation:")
    try:
        from ocr_pipeline.normalize import calculate_item_taxable_value
        for i, item in enumerate(items[:8]):
            tx_stored   = to_float(item.get('taxable_value') or item.get('taxable'))
            tx_computed = calculate_item_taxable_value(item)
            match = "OK" if abs(tx_computed - tx_stored) < 0.02 else f"DIFF stored={tx_stored:.2f} computed={tx_computed:.2f}"
            desc = str(item.get('description') or item.get('item_name') or '')[:35]
            print(f"  {i+1:02d}: {desc!r:<37} stored={tx_stored:8.2f}  computed={tx_computed:8.2f}  {match}")
    except Exception as e:
        print(f"  [ERROR] {e}")

print("\n" + "=" * 100)
print("END OF DATA LINEAGE INVESTIGATION")
print("=" * 100)
