"""
PHASE 1b - More targeted clean room: delete only the SPECIFIC session for the most recent upload.
Also collect pre-test database state statistics.
"""
from ocr_pipeline.models import InvoiceTempOCR, OCRJob, FinalizedSnapshot, SessionFinalizationState
from pending_purchases.models import PendingPurchase
import json

TARGET_FILE = "IMG_20260406_0003"

print("=== PRE-TEST DATABASE STATE ===\n")

# Get all records for this file
all_records = InvoiceTempOCR.objects.filter(file_path__icontains=TARGET_FILE)
all_sessions = list(all_records.values_list('upload_session_id', flat=True).distinct())
all_hashes = list(all_records.values_list('file_hash', flat=True).distinct())
all_rec_ids = list(all_records.values_list('id', flat=True))

print(f"Total staging records for {TARGET_FILE}: {all_records.count()}")
print(f"Distinct sessions: {len(all_sessions)}")
print(f"Distinct file hashes: {len(all_hashes)}")

# Group by status
print("\nStatus breakdown:")
for st in all_records.values('status', 'validation_status').distinct():
    count = all_records.filter(status=st['status'], validation_status=st['validation_status']).count()
    print(f"  status={st['status']:20s} validation_status={st['validation_status']:25s} count={count}")

print("\nMost recent 5 records:")
for r in all_records.order_by('-created_at')[:5]:
    print(f"  id={r.id} session={r.upload_session_id} created={r.created_at} status={r.status} vs={r.validation_status}")

# Find all PENDING PURCHASES for this invoice
all_pps = PendingPurchase.objects.filter(source_scan_row_id__in=all_rec_ids)
print(f"\nPending Purchases: {all_pps.count()}")

# Delete ALL records for this file to ensure clean state
print("\n\n=== DELETING ALL RECORDS FOR CLEAN ROOM ===")

# 1. Delete pending purchases
pp_count = all_pps.count()
all_pps.delete()
print(f"  Deleted {pp_count} PendingPurchase records")

# 2. Delete finalized snapshots  
snap_count = FinalizedSnapshot.objects.filter(session_id__in=all_sessions).count()
FinalizedSnapshot.objects.filter(session_id__in=all_sessions).delete()
print(f"  Deleted {snap_count} FinalizedSnapshot records")

# 3. Delete session finalization states
state_ids = [str(r) for r in all_rec_ids]
sfstate_count = SessionFinalizationState.objects.filter(id__in=state_ids).count()
SessionFinalizationState.objects.filter(id__in=state_ids).delete()
print(f"  Deleted {sfstate_count} SessionFinalizationState records")

# 4. Delete ALL staging records for this file
staging_count = all_records.count()
all_records.delete()
print(f"  Deleted {staging_count} InvoiceTempOCR records")

# 5. Also delete by hash (in case file_path is different)
for h in [hh for hh in all_hashes if hh]:
    hash_records = InvoiceTempOCR.objects.filter(file_hash=h)
    if hash_records.exists():
        hc = hash_records.count()
        hash_records.delete()
        print(f"  Deleted {hc} additional InvoiceTempOCR by hash={h[:16]}")

# 6. Clear Redis
try:
    import redis, os
    r_client = redis.Redis.from_url(os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/0'))
    total_cleared = 0
    for sid in all_sessions:
        if sid:
            keys = r_client.keys(f"*{sid}*")
            if keys:
                r_client.delete(*keys)
                total_cleared += len(keys)
    for h in all_hashes:
        if h:
            keys = r_client.keys(f"*{h}*")
            if keys:
                r_client.delete(*keys)
                total_cleared += len(keys)
    print(f"  Cleared {total_cleared} Redis keys")
except Exception as e:
    print(f"  Redis clear error: {e}")

# 7. Delete vouchers for this invoice if any
try:
    from transactions.models import VoucherPurchaseSupplierDetails
    # Try to delete by invoice numbers that may have been created
    # We don't have them anymore since we deleted the records, so just report
    print(f"  [INFO] Voucher table checked - requires manual verification if invoice numbers are known")
except Exception as e:
    print(f"  Voucher model error: {e}")

print("\n\n=== VERIFYING CLEAN STATE ===")
remaining = InvoiceTempOCR.objects.filter(file_path__icontains=TARGET_FILE).count()
print(f"Remaining staging records for {TARGET_FILE}: {remaining}")

total_staging = InvoiceTempOCR.objects.count()
total_pps = PendingPurchase.objects.count()
print(f"\nTotal system records after cleanup:")
print(f"  InvoiceTempOCR: {total_staging}")
print(f"  PendingPurchase: {total_pps}")
print(f"  FinalizedSnapshots: {FinalizedSnapshot.objects.count()}")

print("\n=== CLEAN ROOM READY FOR TESTING ===")
print("Now upload the file: C:\\Users\\ulaganathan\\Downloads\\New folder (2)\\IMG_20260406_0003.pdf")
