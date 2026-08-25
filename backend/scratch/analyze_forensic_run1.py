import os
import sys
import json

scratch_dir = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(scratch_dir, "forensic_run1_full.json"), "r", encoding="utf-8") as f:
    data = json.load(f)

print("=========================================================")
print("RUN 1 FORENSIC ANALYSIS SUMMARY")
print("=========================================================")

rec = data['staging_record']
print(f"Record ID: {rec['id']}")
print(f"Session ID: {rec['upload_session_id']}")
print(f"Status: {rec['status']}")
print(f"Validation Status: {rec['validation_status']}")
print(f"Processed: {rec['processed']}")
print(f"Supplier Invoice No: {rec['supplier_invoice_no']}")
print(f"GSTIN: {rec['gstin']}")
print(f"Vendor ID: {rec['vendor_id']}")
print(f"Branch: {rec['branch']}")

ext = data['extracted_data']
print("\n--- HEADER DATA ---")
header = ext.get('header', {})
print(f"Supplier Name: {header.get('supplier_name') or header.get('vendor_name')}")
print(f"Supplier GSTIN: {header.get('supplier_gstin') or header.get('gstin')}")
print(f"Buyer Name: {header.get('buyer_name') or header.get('customer_name')}")
print(f"Buyer GSTIN: {header.get('buyer_gstin')}")
print(f"Invoice Number: {header.get('invoice_number') or header.get('supplier_invoice_no')}")
print(f"Invoice Date: {header.get('invoice_date')}")
print(f"Place of Supply: {header.get('place_of_supply') or header.get('supply_place')}")
print(f"Reverse Charge: {header.get('reverse_charge')}")

summary = ext.get('summary', {}) or ext.get('totals', {})
print("\n--- HEADER TOTALS ---")
print(f"Taxable Value: {summary.get('taxable_value') or summary.get('total_taxable_value')}")
print(f"CGST Amount: {summary.get('cgst_amount') or summary.get('total_cgst')}")
print(f"SGST Amount: {summary.get('sgst_amount') or summary.get('total_sgst')}")
print(f"IGST Amount: {summary.get('igst_amount') or summary.get('total_igst')}")
print(f"Total GST: {summary.get('total_tax') or summary.get('total_gst')}")
print(f"Invoice Total: {summary.get('invoice_total') or summary.get('grand_total') or summary.get('total_amount')}")
print(f"Round Off: {summary.get('round_off') or summary.get('rounding_adjustment')}")

items = ext.get('items', [])
print(f"\n--- LINE ITEMS ({len(items)}) ---")
calc_taxable_sum = 0.0
calc_cgst_sum = 0.0
calc_sgst_sum = 0.0
calc_igst_sum = 0.0
calc_total_sum = 0.0

for idx, itm in enumerate(items, 1):
    desc = itm.get('description') or itm.get('item_name')
    hsn = itm.get('hsn_sac') or itm.get('hsn')
    qty = float(itm.get('quantity') or 0)
    rate = float(itm.get('rate') or itm.get('unit_price') or 0)
    discount = float(itm.get('discount') or itm.get('discount_amount') or 0)
    taxable = float(itm.get('taxable_value') or itm.get('taxable_amount') or 0)
    gst_rate = float(itm.get('gst_rate') or 0)
    cgst_amt = float(itm.get('cgst_amount') or 0)
    sgst_amt = float(itm.get('sgst_amount') or 0)
    igst_amt = float(itm.get('igst_amount') or 0)
    inv_val = float(itm.get('invoice_value') or itm.get('total_value') or itm.get('item_total') or 0)

    gross = qty * rate
    calc_taxable = gross - discount
    calc_gst = taxable * (gst_rate / 100.0)

    calc_taxable_sum += taxable
    calc_cgst_sum += cgst_amt
    calc_sgst_sum += sgst_amt
    calc_igst_sum += igst_amt
    calc_total_sum += inv_val

    print(f"Item #{idx}: {desc}")
    print(f"  HSN: {hsn} | Qty: {qty} | Rate: {rate} | Gross (Qty*Rate): {gross:.2f} | Discount: {discount:.2f} | Taxable: {taxable:.2f}")
    print(f"  GST Rate: {gst_rate}% | CGST: {cgst_amt:.2f} | SGST: {sgst_amt:.2f} | IGST: {igst_amt:.2f} | Total: {inv_val:.2f}")

print("\n--- MATHEMATICAL AUDIT ---")
header_taxable = float(summary.get('taxable_value') or summary.get('total_taxable_value') or 0)
header_cgst = float(summary.get('cgst_amount') or summary.get('total_cgst') or 0)
header_sgst = float(summary.get('sgst_amount') or summary.get('total_sgst') or 0)
header_igst = float(summary.get('igst_amount') or summary.get('total_igst') or 0)
header_total = float(summary.get('invoice_total') or summary.get('grand_total') or summary.get('total_amount') or 0)
round_off = float(summary.get('round_off') or summary.get('rounding_adjustment') or 0)

print(f"SUM(Item Taxable Values) = {calc_taxable_sum:.2f} vs Header Taxable Value = {header_taxable:.2f} (Diff: {calc_taxable_sum - header_taxable:.2f})")
print(f"SUM(Item CGST) = {calc_cgst_sum:.2f} vs Header CGST = {header_cgst:.2f} (Diff: {calc_cgst_sum - header_cgst:.2f})")
print(f"SUM(Item SGST) = {calc_sgst_sum:.2f} vs Header SGST = {header_sgst:.2f} (Diff: {calc_sgst_sum - header_sgst:.2f})")
print(f"SUM(Item IGST) = {calc_igst_sum:.2f} vs Header IGST = {header_igst:.2f} (Diff: {calc_igst_sum - header_igst:.2f})")
header_tax_sum = header_cgst + header_sgst + header_igst
calc_tax_sum = calc_cgst_sum + calc_sgst_sum + calc_igst_sum
print(f"Calculated Total GST = {calc_tax_sum:.2f} vs Header Total GST = {header_tax_sum:.2f}")
print(f"Header Taxable + Header GST + RoundOff = {header_taxable + header_tax_sum + round_off:.2f} vs Header Invoice Total = {header_total:.2f}")

print("\n--- PAGE BY PAGE BREAKDOWN ---")
for p in data['pages']:
    p_no = p['page_number']
    p_payload = p['canonical_payload']
    p_items = p_payload.get('items', []) or p_payload.get('sections', {}).get('items', []) or []
    print(f"Page {p_no}: is_failed={p['is_failed']}, items count={len(p_items)}")
    for itm in p_items:
        print(f"  - {itm.get('description') or itm.get('item_name')} (Qty: {itm.get('quantity')}, Rate: {itm.get('rate')}, Taxable: {itm.get('taxable_value')})")

print("\n--- VALIDATION / GST AUDIT TRAIL ---")
val_trail = ext.get('gst_audit_trail') or ext.get('validation_details') or ext.get('validation_audit')
if val_trail:
    print(json.dumps(val_trail, indent=2, default=str))
else:
    print("No explicit gst_audit_trail key in root extracted_data.")
