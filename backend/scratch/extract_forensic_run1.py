import os
import sys
import json
from decimal import Decimal

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
import django
django.setup()

from ocr_pipeline.models import InvoiceTempOCR, SessionFinalizationState, InvoicePageResult, FinalizedSnapshot
from vouchers.models import BulkInvoiceJob, InvoiceProcessingItem
from accounting.models_voucher_purchase import VoucherPurchaseSupplierDetails, VoucherPurchaseItem, VoucherPurchaseSupplyINRDetails
from vendors.models import VendorMasterBasicDetail

def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    return str(obj)

record_id = 1013204
record = InvoiceTempOCR.objects.get(id=record_id)
session_id = record.upload_session_id

data = {
    "staging_record": {
        "id": record.id,
        "file_hash": record.file_hash,
        "tenant_id": str(record.tenant_id),
        "file_path": record.file_path,
        "upload_session_id": record.upload_session_id,
        "voucher_type": record.voucher_type,
        "upload_type": record.upload_type,
        "status": record.status,
        "validation_status": record.validation_status,
        "processed": record.processed,
        "supplier_invoice_no": record.supplier_invoice_no,
        "gstin": record.gstin,
        "vendor_id": record.vendor_id,
        "branch": record.branch,
        "normalized_invoice_no": record.normalized_invoice_no,
        "vendor_confidence": record.vendor_confidence,
        "gstin_confidence": record.gstin_confidence,
        "invoice_number_confidence": record.invoice_number_confidence,
        "workflow_version": record.workflow_version,
        "created_at": str(getattr(record, 'created_at', None)),
    },
    "barrier_state": {},
    "pages": [],
    "snapshot": None,
    "extracted_data": record.extracted_data,
    "vouchers": []
}

barrier = SessionFinalizationState.objects.filter(id=str(record_id)).first()
if barrier:
    data["barrier_state"] = {
        "expected_pages": barrier.expected_pages,
        "completed_pages": barrier.completed_pages,
        "failed_pages": barrier.failed_pages,
        "ai_completed_pages": barrier.ai_completed_pages,
        "snapshot_created": barrier.snapshot_created,
        "assembly_complete": barrier.assembly_complete,
        "continuation_merge_complete": barrier.continuation_merge_complete,
        "materialization_complete": barrier.materialization_complete,
        "export_complete": barrier.export_complete,
        "status": barrier.status
    }

for p in InvoicePageResult.objects.filter(record_id=record_id).order_by('page_number'):
    data["pages"].append({
        "page_number": p.page_number,
        "is_failed": p.is_failed,
        "created_at": str(p.created_at),
        "canonical_payload": p.canonical_payload
    })

snap = FinalizedSnapshot.objects.filter(session_id=session_id).first()
if snap:
    data["snapshot"] = {
        "id": snap.id,
        "session_id": snap.session_id,
        "created_at": str(snap.created_at),
        "snapshot_json": snap.snapshot_json
    }

for v in VoucherPurchaseSupplierDetails.objects.filter(supplier_invoice_no=record.supplier_invoice_no, gstin=record.gstin):
    v_dict = {
        "id": v.id,
        "purchase_voucher_no": v.purchase_voucher_no,
        "date": str(v.date),
        "supplier_invoice_no": v.supplier_invoice_no,
        "supplier_invoice_date": str(v.supplier_invoice_date),
        "vendor_name": v.vendor_name,
        "gstin": v.gstin,
        "branch": v.branch,
        "items": []
    }
    for itm in VoucherPurchaseItem.objects.filter(supplier_details_id=v.id):
        v_dict["items"].append({
            "item_code": itm.item_code,
            "item_name": itm.item_name,
            "hsn_sac": itm.hsn_sac,
            "quantity": float(itm.quantity),
            "rate": float(itm.rate),
            "taxable_value": float(itm.taxable_value),
            "gst_rate": float(itm.gst_rate),
            "cgst_amount": float(itm.cgst_amount),
            "sgst_amount": float(itm.sgst_amount),
            "igst_amount": float(itm.igst_amount),
            "invoice_value": float(itm.invoice_value)
        })
    data["vouchers"].append(v_dict)

out_file = os.path.join(current_dir, "forensic_run1_full.json")
with open(out_file, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, default=decimal_default)

print(f"Exported detailed forensic data to {out_file}")
