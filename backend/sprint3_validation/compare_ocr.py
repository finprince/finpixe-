import json

ocr = json.load(open("sprint3_validation/reports/OCR_RAW_TRACE.json", encoding="utf-8"))
ext = json.load(open("sprint3_validation/reports/MISTRAL_FULL_EXTRACTION.json", encoding="utf-8"))

for fname, record_data in ocr.items():
    print("=" * 60)
    print("Filename:", fname)
    rec_id = record_data["record_id"]
    match = next((r for r in ext if r["id"] == rec_id), None)
    if match:
        print("EXTRACTED CANONICAL DATA:")
        print("  invoice_no:    ", match.get("invoice_no"))
        print("  invoice_date:  ", match.get("invoice_date"))
        print("  vendor_name:   ", match.get("vendor_name"))
        print("  vendor_gstin:  ", match.get("vendor_gstin"))
        print("  buyer_name:    ", match.get("buyer_name"))
        print("  buyer_gstin:   ", match.get("buyer_gstin"))
        print("  taxable_amount:", match.get("taxable_amount"))
        print("  grand_total:   ", match.get("grand_total"))
        print("  items count:   ", match.get("item_count"))
        for idx, it in enumerate(match.get("items", [])):
            print(f"    [{idx}] hsn={it['hsn']} desc={repr(it['desc'][:55])} qty={it['qty']} rate={it['rate']} taxable={it['taxable']}")
    else:
        print("No matching record in extracted dump.")
