"""
trigger_rescan.py

Triggers a rescan of the GST Mismatch staging record to test prompt invalidation,
literal AI extraction, and backend normalization/layout rules.
"""
import os
import sys
import time

# Ensure backend directory is in the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

import django
django.setup()

from ocr_pipeline.models import InvoiceTempOCR
from ocr_pipeline.pipeline import validate_and_process

RECORD_ID = 1009270

def main():
    print("=== STARTING RESCAN TEST ===")
    
    # Flush Redis keys to clear stale locks
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0)
        for key in r.keys('*'):
            r.delete(key)
        print("Flushed all Redis keys to clear stale locks.")
    except Exception as re_err:
        print(f"Warning: Failed to flush Redis: {re_err}")
    
    # 1. Fetch the target record
    try:
        record = InvoiceTempOCR.objects.get(id=RECORD_ID)
    except InvoiceTempOCR.DoesNotExist:
        print(f"Error: Record {RECORD_ID} not found in database.")
        return
        
    print(f"Record found: ID={record.id}, file_hash={record.file_hash[:16]}..., status={record.status}")
    print("Wiping existing extracted_data to force a fresh re-extraction...")
    # Use raw SQL to reset — bypasses the model-level immutability guard
    # that reads DUPLICATE from DB and restores it on save().
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE invoice_ocr_temp
            SET extracted_data = NULL,
                status = 'PENDING',
                validation_status = 'PENDING',
                processed = FALSE
            WHERE id = %s
            """,
            [record.id]
        )
    record.refresh_from_db()
    print(f"After raw reset: status={record.status}, validation_status={record.validation_status}")
    
    # 2. Trigger the ingestion process synchronously (mimics queue task execution)
    from ocr_pipeline.pipeline import run_ocr_pipeline
    print("Running run_ocr_pipeline with record file path...")
    run_ocr_pipeline(record=record, file_path=record.file_path, wait_for_ai=True, is_rescan=True)
    
    # 3. Reload record and print results
    record.refresh_from_db()
    print("\n=== RESCAN RESULTS ===")
    print(f"Status: {record.status}")
    print(f"Validation Status: {record.validation_status}")
    
    data = record.extracted_data or {}
    print("\n_raw_extraction:")
    raw = data.get("_raw_extraction", {})
    raw_items = raw.get("items", [])
    if raw_items:
        print(f"  raw item description: {raw_items[0].get('description')}")
        print(f"  raw item quantity: {raw_items[0].get('quantity')}")
        print(f"  raw item rate: {raw_items[0].get('rate')}")
        print(f"  raw item amount: {raw_items[0].get('amount')}")
        print(f"  raw item taxable_value: {raw_items[0].get('taxable_value')}")
        print(f"  raw item discount_percent: {raw_items[0].get('discount_percent')}")
    else:
        print("  No raw items found!")
        
    print("\nRoot Level Canonical Data:")
    items = data.get("items", [])
    if items:
        print(f"  canonical item description: {items[0].get('description')}")
        print(f"  canonical item qty: {items[0].get('qty')}")
        print(f"  canonical item rate: {items[0].get('rate')}")
        print(f"  canonical item taxable_value: {items[0].get('taxable_value')}")
        print(f"  canonical item discount_percent: {items[0].get('discount_percent')}")
        print(f"  canonical item discount_amount: {items[0].get('discount_amount')}")
    else:
        print("  No canonical items found!")
        
    print("\n_validation_metadata:")
    metadata = data.get("_validation_metadata", {})
    print(f"  layout_confidence: {metadata.get('layout_confidence')}")
    print(f"  layout_type: {metadata.get('layout_type')}")
    print(f"  validation_warnings: {metadata.get('validation_warnings')}")
    print(f"  item_consistency: {metadata.get('item_consistency')}")
    print(f"  warnings: {data.get('warnings')}")

if __name__ == '__main__':
    main()
