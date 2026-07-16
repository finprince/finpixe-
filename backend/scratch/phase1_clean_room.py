"""
PHASE 1 - Clean Room Setup for Invoice: IMG_20260406_0003.pdf
Deletes ALL records related to this invoice and verifies clean state.
"""
import os, json, subprocess
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings.dev')

import django
django.setup()

import django_redis
from django.core.cache import cache
from ocr_pipeline.models import InvoiceTempOCR, OCRJob, OCRTask, FinalizedSnapshot, SessionFinalizationState
from pending_purchases.models import PendingPurchase

TARGET_FILENAME = "IMG_20260406_0003.pdf"

print("=== PHASE 1: CLEAN ROOM SETUP ===\n")
print(f"Target invoice: {TARGET_FILENAME}\n")

# --- 1. Find all staging records for this file ---
staging_records = InvoiceTempOCR.objects.filter(file_path__icontains="IMG_20260406_0003")
session_ids = list(staging_records.values_list('upload_session_id', flat=True).distinct())
file_hashes = list(staging_records.values_list('file_hash', flat=True).distinct())
record_ids = list(staging_records.values_list('id', flat=True).distinct())
group_ids = list(staging_records.values_list('group_id', flat=True).distinct())

print(f"Found staging records: {staging_records.count()}")
print(f"  Record IDs: {record_ids}")
print(f"  Session IDs: {session_ids}")
print(f"  File Hashes: {file_hashes}")
print(f"  Group IDs: {group_ids}")

# Also find by hash if any related records exist
if file_hashes:
    related_by_hash = InvoiceTempOCR.objects.filter(file_hash__in=[h for h in file_hashes if h])
    print(f"\nAll records with same file_hash: {related_by_hash.count()}")
    for r in related_by_hash:
        print(f"  id={r.id} session={r.upload_session_id} status={r.status} validation_status={r.validation_status}")

# --- 2. Find all related OCR jobs ---
print("\n--- OCR JOBS ---")
related_jobs = []
for sid in session_ids:
    if sid:
        jobs = OCRJob.objects.filter(upload_session_id=sid)
        print(f"  Session {sid}: {jobs.count()} jobs")
        related_jobs += list(jobs.values_list('id', flat=True))

# --- 3. Find pending purchases ---
print("\n--- PENDING PURCHASES ---")
related_pps = PendingPurchase.objects.filter(source_scan_row_id__in=record_ids)
print(f"  Count: {related_pps.count()}")
for pp in related_pps:
    print(f"  PP id={pp.id} invoice={pp.invoice_number} status={pp.pending_purchase_status}")

# --- 4. Find finalized snapshots ---
print("\n--- FINALIZED SNAPSHOTS ---")
related_snaps = FinalizedSnapshot.objects.filter(session_id__in=[s for s in session_ids if s])
print(f"  Count: {related_snaps.count()}")

# --- 5. Find session finalization states ---
print("\n--- SESSION FINALIZATION STATES ---")
related_states = SessionFinalizationState.objects.filter(id__in=[str(r) for r in record_ids])
print(f"  Count: {related_states.count()}")

# --- 6. Find vouchers ---
print("\n--- VOUCHERS ---")
try:
    from transactions.models import VoucherPurchaseSupplierDetails
    related_vouchers = VoucherPurchaseSupplierDetails.objects.filter(
        ocr_staging_id__in=record_ids
    )
    print(f"  Vouchers by staging id: {related_vouchers.count()}")
    # Also check by invoice_no if we can find it
    for r in staging_records:
        if r.supplier_invoice_no:
            v = VoucherPurchaseSupplierDetails.objects.filter(supplier_invoice_no=r.supplier_invoice_no)
            print(f"  Vouchers by invoice_no={r.supplier_invoice_no}: {v.count()}")
except Exception as e:
    print(f"  [VOUCHER LOOKUP ERROR]: {e}")

# --- 7. Redis cache/locks ---
print("\n--- REDIS STATE ---")
try:
    import redis
    r_client = redis.Redis.from_url(os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/0'))
    for sid in session_ids:
        if sid:
            redis_keys = r_client.keys(f"*{sid}*")
            print(f"  Session {sid}: {len(redis_keys)} Redis keys")
            for k in redis_keys[:10]:
                print(f"    {k.decode()}")
    for h in file_hashes:
        if h:
            redis_keys_hash = r_client.keys(f"*{h}*")
            print(f"  Hash {h[:16]}: {len(redis_keys_hash)} Redis keys")
except Exception as e:
    print(f"  [REDIS ERROR]: {e}")

print("\n\n=== CLEAN ROOM DELETION ===")
confirm = "YES"  # Auto-confirm for script execution

if confirm == "YES":
    deleted = {}
    
    # Delete in order: PP first, then staging, then jobs, then snapshots, then states
    if related_pps.count() > 0:
        deleted['pending_purchases'] = related_pps.count()
        related_pps.delete()
    
    if related_snaps.count() > 0:
        deleted['finalized_snapshots'] = related_snaps.count()
        related_snaps.delete()
        
    if related_states.count() > 0:
        deleted['session_finalization_states'] = related_states.count()
        related_states.delete()
    
    # Delete all staging records (including sub-pages via group_id)
    all_staging_to_delete = InvoiceTempOCR.objects.filter(
        upload_session_id__in=[s for s in session_ids if s]
    )
    deleted['staging_records'] = all_staging_to_delete.count()
    all_staging_to_delete.delete()
    
    # Also delete by file hash
    if file_hashes:
        hash_records = InvoiceTempOCR.objects.filter(file_hash__in=[h for h in file_hashes if h])
        if hash_records.exists():
            deleted['staging_records_by_hash'] = hash_records.count()
            hash_records.delete()
    
    # Delete OCR jobs
    if related_jobs:
        from ocr_pipeline.models import OCRJob
        del_jobs = OCRJob.objects.filter(id__in=related_jobs)
        deleted['ocr_jobs'] = del_jobs.count()
        del_jobs.delete()
    
    # Clear Redis
    try:
        for sid in session_ids:
            if sid:
                redis_keys = r_client.keys(f"*{sid}*")
                if redis_keys:
                    r_client.delete(*redis_keys)
                    print(f"  Cleared {len(redis_keys)} Redis keys for session {sid}")
        for h in file_hashes:
            if h:
                redis_keys_hash = r_client.keys(f"*{h}*")
                if redis_keys_hash:
                    r_client.delete(*redis_keys_hash)
                    print(f"  Cleared {len(redis_keys_hash)} Redis keys for hash {h[:16]}")
    except Exception as e:
        print(f"  [REDIS CLEAR ERROR]: {e}")
    
    print(f"\nDeletion summary: {deleted}")
else:
    print("Skipping deletion (no confirmation)")

print("\n=== VERIFYING CLEAN STATE ===")
remaining = InvoiceTempOCR.objects.filter(file_path__icontains="IMG_20260406_0003").count()
print(f"Remaining staging records: {remaining}")

# Count all staging records in system
total_staging = InvoiceTempOCR.objects.count()
total_pps = PendingPurchase.objects.count()
print(f"\nSystem-wide state:")
print(f"  Total InvoiceTempOCR records: {total_staging}")
print(f"  Total PendingPurchase records: {total_pps}")

print("\n=== PHASE 1 COMPLETE: CLEAN ROOM READY ===")
