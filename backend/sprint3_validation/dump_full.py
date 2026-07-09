import os, sys, json
sys.path.insert(0,".")
os.environ.setdefault("DJANGO_SETTINGS_MODULE","backend.settings")
import django; django.setup()
from ocr_pipeline.models import InvoiceTempOCR

records = InvoiceTempOCR.objects.filter(id__gte=1008375,id__lte=1008397).order_by("id")
output=[]
for r in records:
    data = r.extracted_data or {}
    items = data.get("line_items", data.get("items",[]))
    rec = {
        "id":r.id, "status":r.status,
        "filename":(r.file_path or "").split("/")[-1][-50:],
        "invoice_no":data.get("invoice_no") or data.get("canonical_invoice_no"),
        "invoice_date":data.get("invoice_date") or data.get("canonical_invoice_date"),
        "vendor_name":data.get("vendor_name") or data.get("canonical_vendor_name"),
        "vendor_gstin":data.get("vendor_gstin") or data.get("canonical_vendor_gstin"),
        "buyer_name":data.get("buyer_name") or data.get("canonical_buyer_name"),
        "buyer_gstin":data.get("buyer_gstin") or data.get("canonical_buyer_gstin"),
        "taxable_amount":data.get("total_taxable_value"),
        "cgst_total":data.get("total_cgst"),
        "sgst_total":data.get("total_sgst"),
        "igst_total":data.get("total_igst"),
        "grand_total":data.get("total_invoice_value"),
        "round_off":data.get("round_off"),
        "low_confidence":data.get("low_confidence"),
        "validation_warnings":data.get("validation_warnings",[]),
        "source_page":data.get("_page_no"),
        "page_role":data.get("_page_role"),
        "item_count":len(items),
        "items":[{
            "desc":(it.get("description") or it.get("raw_item_name") or "")[:80],
            "hsn":it.get("hsn_sac") or it.get("hsn"),
            "qty":it.get("qty"), "rate":it.get("rate"),
            "taxable":it.get("taxable_value"),
            "cgst_rate":it.get("cgst_rate"), "total":it.get("total_amount"),
            "discount":it.get("discount"),
        } for it in items]
    }
    output.append(rec)

with open("sprint3_validation/reports/MISTRAL_FULL_EXTRACTION.json","w",encoding="utf-8") as f:
    json.dump(output,f,indent=2,ensure_ascii=False)

print("id | status | invoice_no | vendor_name | items | grand_total | taxable | cgst | sgst | igst | low_conf | warnings")
for r in output:
    print(r["id"],"|",r["status"],"|",r["invoice_no"],"|",str(r["vendor_name"])[:25],"|",r["item_count"],"|",r["grand_total"],"|",r["taxable_amount"],"|",r["cgst_total"],"|",r["sgst_total"],"|",r["igst_total"],"|",r["low_confidence"],"|",r["validation_warnings"])
