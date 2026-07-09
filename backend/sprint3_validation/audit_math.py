import json

ext = json.load(open("sprint3_validation/reports/MISTRAL_FULL_EXTRACTION.json", encoding="utf-8"))

print(f"{'ID':8s} | {'Inv No':15s} | {'Taxable':10s} | {'CGST':8s} | {'SGST':8s} | {'IGST':8s} | {'Expected':10s} | {'Actual':10s} | {'Diff':8s} | {'Match'}")
print("-" * 95)
for r in ext:
    taxable = r.get("taxable_amount") or 0.0
    cgst = r.get("cgst_total") or 0.0
    sgst = r.get("sgst_total") or 0.0
    igst = r.get("igst_total") or 0.0
    actual = r.get("grand_total") or 0.0
    
    expected = taxable + cgst + sgst + igst
    diff = abs(expected - actual)
    match_status = "PASS" if diff < 1.0 else "FAIL"
    
    inv_no = r.get("invoice_no") or "N/A"
    print(f"{r['id']:8d} | {inv_no:15s} | {taxable:10.2f} | {cgst:8.2f} | {sgst:8.2f} | {igst:8.2f} | {expected:10.2f} | {actual:10.2f} | {diff:8.2f} | {match_status}")
