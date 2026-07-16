"""
COMPREHENSIVE CLEAN-ROOM RESET
Cleans:
1. Redis: FLUSHALL
2. SQS: Deletes/Purges all messages in roles queues
3. Database: Deletes staging, page results, jobs, pending purchases, finalization states, vouchers, ledger entries, etc.
4. Media Files: Cleans bulk_pipeline upload directory
"""
import os
import sys
import django
import shutil

# Setup Django
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

import redis
import boto3
from django.db import connections
from core.sqs import queue_service
from ocr_pipeline.models import (
    InvoiceTempOCR, InvoicePageResult, OCRJob, OCRTask, 
    FinalizedSnapshot, SessionFinalizationState, AICache
)
from pending_purchases.models import PendingPurchase
from accounting.models_voucher_purchase import VoucherPurchaseSupplierDetails, VoucherPurchaseItem, VoucherPurchaseDueDetails
from django.db import transaction

def clean_redis():
    print("\n--- Cleaning Redis ---")
    try:
        redis_url = os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/0')
        r = redis.Redis.from_url(redis_url)
        r.flushall()
        print("  Redis FLUSHALL complete.")
    except Exception as e:
        print(f"  Redis cleanup error: {e}")

def clean_sqs():
    print("\n--- Cleaning SQS Queues ---")
    roles = ['ingestion', 'ai', 'assembly', 'finalize', 'export', 'materialization']
    client = queue_service._get_sqs_client()
    for role in roles:
        try:
            url = queue_service._get_queue_url(role)
            if url:
                print(f"  Purging SQS queue for role '{role}' ({url})...")
                try:
                    client.purge_queue(QueueUrl=url)
                    print(f"    Purged queue '{role}' successfully.")
                except Exception as purge_err:
                    # If purge limit exceeded, receive and delete messages in loop
                    print(f"    Purge failed ({purge_err}). Discarding messages manually...")
                    count = 0
                    while True:
                        res = client.receive_message(
                            QueueUrl=url,
                            MaxNumberOfMessages=10,
                            WaitTimeSeconds=1
                        )
                        messages = res.get('Messages', [])
                        if not messages:
                            break
                        for msg in messages:
                            client.delete_message(
                                QueueUrl=url,
                                ReceiptHandle=msg['ReceiptHandle']
                            )
                            count += 1
                    print(f"    Manually discarded {count} messages from '{role}' queue.")
        except Exception as e:
            print(f"    Error cleaning queue for role '{role}': {e}")

def clean_database():
    print("\n--- Cleaning Database Records ---")
    target_invoice_no = "3049/25-26"
    target_pdf = "IMG_20260406_0003"
    
    with transaction.atomic():
        # Find related records
        recs = InvoiceTempOCR.objects.filter(
            file_path__icontains=target_pdf
        ) | InvoiceTempOCR.objects.filter(
            supplier_invoice_no=target_invoice_no
        )
        rec_ids = list(recs.values_list('id', flat=True))
        session_ids = list(recs.values_list('upload_session_id', flat=True).distinct())
        
        print(f"  Found {len(rec_ids)} related temporary OCR records: {rec_ids}")
        
        # 1. Delete Voucher / Ledger Entries related to these records
        if rec_ids:
            vouchers = VoucherPurchaseSupplierDetails.objects.filter(
                supplier_invoice_no=target_invoice_no
            )
            v_ids = list(vouchers.values_list('id', flat=True))
            print(f"  Found {len(v_ids)} related vouchers: {v_ids}")
            
            # Delete voucher sub-records
            if v_ids:
                VoucherPurchaseItem.objects.filter(voucher_id__in=v_ids).delete()
                VoucherPurchaseDueDetails.objects.filter(voucher_id__in=v_ids).delete()
                vouchers.delete()
                print("    Vouchers and items deleted.")
            
            # Delete pending purchases
            pps = PendingPurchase.objects.filter(source_scan_row_id__in=rec_ids)
            print(f"    Deleting {pps.count()} pending purchases...")
            pps.delete()
            
            # Delete finalized snapshots and finalization states
            snapshots = FinalizedSnapshot.objects.filter(session_id__in=[s for s in session_ids if s])
            print(f"    Deleting {snapshots.count()} finalized snapshots...")
            snapshots.delete()
            
            states = SessionFinalizationState.objects.filter(id__in=[str(r) for r in rec_ids])
            print(f"    Deleting {states.count()} session finalization states...")
            states.delete()
            
            # Delete page results and tasks
            pages = InvoicePageResult.objects.filter(record_id__in=rec_ids)
            print(f"    Deleting {pages.count()} invoice page results...")
            pages.delete()
            
            # Delete jobs and tasks
            OCRTask.objects.all().delete()
            OCRJob.objects.all().delete()
            
            # Clear AICache entries containing target invoice number or text
            caches = AICache.objects.filter(payload__icontains=target_invoice_no) | AICache.objects.filter(payload__icontains=target_pdf)
            print(f"    Deleting {caches.count()} AICache entries...")
            caches.delete()
            
            # Finally delete InvoiceTempOCR records
            recs.delete()
            print("    InvoiceTempOCR records deleted.")

def clean_media_files():
    print("\n--- Cleaning Media / Temporary Files ---")
    bulk_dir = os.path.join(base_dir, "media", "bulk_pipeline")
    if os.path.exists(bulk_dir):
        # Iterate over ocr and snapshots subfolders and empty them
        for sub in ['ocr', 'snapshots']:
            sub_path = os.path.join(bulk_dir, sub)
            if os.path.exists(sub_path):
                for item in os.listdir(sub_path):
                    item_path = os.path.join(sub_path, item)
                    try:
                        if os.path.isdir(item_path):
                            shutil.rmtree(item_path)
                            print(f"  Removed folder: {item_path}")
                        else:
                            os.remove(item_path)
                            print(f"  Removed file: {item_path}")
                    except Exception as e:
                        print(f"  Error deleting {item_path}: {e}")
    print("  Media folders cleaned.")

def main():
    print("=" * 80)
    print("RUNNING CLEAN-ROOM RESET")
    print("=" * 80)
    clean_redis()
    clean_sqs()
    clean_database()
    clean_media_files()
    print("\n" + "=" * 80)
    print("CLEAN-ROOM RESET COMPLETE")
    print("=" * 80)

if __name__ == '__main__':
    main()
