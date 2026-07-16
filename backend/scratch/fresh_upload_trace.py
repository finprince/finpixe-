"""
FRESH UPLOAD AND RUNTIME PIPELINE TRACE (CHILD AWARE & MULTIPROCESSING SAFE)
===========================================================================
Kicks off a fresh pipeline run for IMG_20260406_0003.pdf
and traces the GST variables on the split page 14 child record.
Cleans up the database records afterwards to keep a clean environment.
"""
import os, sys

def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    import django
    django.setup()

    from ocr_pipeline.models import InvoiceTempOCR, SessionFinalizationState
    from core.models import Branch
    from ocr_pipeline.pipeline import run_ocr_pipeline, run_gst_validation_engine
    from pending_purchases.models import PendingPurchase
    from django.db import transaction
    import uuid

    PDF_PATH = r"C:\Users\ulaganathan\Downloads\New folder (2)\IMG_20260406_0003.pdf"

    # Find tenant ID
    branch = Branch.objects.first()
    tenant_id = str(branch.id) if branch else "system"

    session_id = f"dry_run_session_{uuid.uuid4()}"

    print(f"Creating parent staging record for IMG_20260406_0003.pdf...")
    with transaction.atomic():
        record = InvoiceTempOCR.objects.create(
            tenant_id=tenant_id,
            status="PENDING",
            voucher_type="Purchase",
            file_path=f"LOCAL://dry_run/IMG_20260406_0003.pdf",
            upload_session_id=session_id,
        )
        SessionFinalizationState.objects.get_or_create(
            id=str(record.id),
            defaults={"expected_pages": 19, "total_pages_expected": 19}
        )

    print(f"Running pipeline for parent record ID: {record.id}...")
    with open(PDF_PATH, "rb") as f:
        file_bytes = f.read()

    # Run the pipeline
    pipeline_res = run_ocr_pipeline(
        file_bytes=file_bytes,
        record=record,
        wait_for_ai=True,
        file_path=PDF_PATH
    )

    # Load child records created in this session
    print(f"Querying child records created for session {session_id}...")
    child_records = list(InvoiceTempOCR.objects.filter(upload_session_id=session_id))
    print(f"Found {len(child_records)} records in session:")
    for r in child_records:
        ext_data = r.extracted_data or {}
        inv_no = r.supplier_invoice_no or ext_data.get("invoice_no") or "?"
        print(f"  - Record {r.id}: Invoice {inv_no} | Status: {r.status} | Validation: {r.validation_status}")

    # Find the record containing EIS/25-26/1014 or HSN 8210
    target_record = None
    for r in child_records:
        ext_data = r.extracted_data or {}
        inv_no = r.supplier_invoice_no or ext_data.get("invoice_no") or ""
        if "1014" in inv_no:
            target_record = r
            break

    if not target_record:
        # Try looking for HSN 8210 in items
        for r in child_records:
            ext_data = r.extracted_data or {}
            items = ext_data.get("items", [])
            if any("8210" in str(i.get("hsn_sac") or i.get("hsn_code") or "") for i in items):
                target_record = r
                break

    if target_record:
        print(f"\nTarget record found: {target_record.id}")
        ext = target_record.extracted_data or {}
        raw_ext = ext.get("_raw_extraction") or {}

        def get_hsn_item(items, hsn):
            for itm in items:
                if hsn in str(itm.get("hsn_sac") or itm.get("hsn_code") or ""):
                    return itm
            return {}

        print("\n" + "="*72)
        print(f"E2E PIPELINE RUN GST VARIABLE TRACE FOR TARGET RECORD {target_record.id}")
        print("="*72)

        raw_item = get_hsn_item(raw_ext.get("items", []), "8210")
        print(f"1. Raw AI Output (_raw_extraction):")
        print(f"   cgst_rate:         {raw_item.get('cgst_rate')}")
        print(f"   sgst_rate:         {raw_item.get('sgst_rate')}")
        print(f"   cgst_amount:       {raw_item.get('cgst_amount') or raw_item.get('cgst')}")
        print(f"   sgst_amount:       {raw_item.get('sgst_amount') or raw_item.get('sgst')}")

        norm_item = get_hsn_item(ext.get("items", []), "8210")
        print(f"\n2. After normalize.py:")
        print(f"   cgst_rate:         {norm_item.get('cgst_rate')}")
        print(f"   sgst_rate:         {norm_item.get('sgst_rate')}")
        print(f"   cgst_amount:       {norm_item.get('cgst_amount') or norm_item.get('cgst')}")
        print(f"   sgst_amount:       {norm_item.get('sgst_amount') or norm_item.get('sgst')}")

        print(f"\n3. Persisted in InvoiceTempOCR.extracted_data:")
        print(f"   cgst_rate:         {norm_item.get('cgst_rate')}")
        print(f"   sgst_rate:         {norm_item.get('sgst_rate')}")
        print(f"   cgst_amount:       {norm_item.get('cgst')}")
        print(f"   sgst_amount:       {norm_item.get('sgst')}")

        # GST Validation engine trail
        trail = ext.get("gst_audit_trail", {})
        print(f"\n4. GST Validation Engine output:")
        print(f"   Status:            {trail.get('validation_status')}")
        print(f"   Expected CGST/SGST: {trail.get('expected_tax_values', {}).get('cgst')}")
        print(f"   Extracted CGST/SGST:{trail.get('extracted_tax_values', {}).get('cgst')}")
        print(f"   Difference:        {trail.get('difference_amount')}")

        # Inspect Pending Purchase record
        pp_item = PendingPurchase.objects.filter(scan_session_id=session_id).first()
        if pp_item:
            print(f"\n5. Pending Purchase DB entry:")
            print(f"   ID:                {pp_item.id}")
            print(f"   GST Audit Trail:   {pp_item.gst_audit_trail}")
    else:
        print("\nTarget record containing EIS/25-26/1014 or HSN 8210 was NOT found among child records!")

    # Clean up all created records in session
    print("\nCleaning up staging records...")
    all_ids = [r.id for r in child_records] + [record.id]
    # Delete Pending purchases first to avoid FK constraint error
    PendingPurchase.objects.filter(scan_session_id=session_id).delete()
    InvoiceTempOCR.objects.filter(id__in=all_ids).delete()
    SessionFinalizationState.objects.filter(id__in=[str(x) for x in all_ids]).delete()
    print(f"Cleaned up session {session_id} successfully.")
    print("="*72)

if __name__ == '__main__':
    main()
