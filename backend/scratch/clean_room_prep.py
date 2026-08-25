import os
import sys
import time
import subprocess
import psutil
import json

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import boto3
import redis
from dotenv import load_dotenv

load_dotenv(os.path.join(project_root, '.env'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

import django
django.setup()

from django.db import connections
from core.sqs import queue_service

def step1_stop_workers():
    print("--- 1. STOPPING EXISTING WORKERS ---")
    current_pid = os.getpid()
    patterns = ['worker_watchdog.py', 'unified_worker.py', 'start_cluster.py']
    terminated = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info.get('cmdline')
            if not cmdline or proc.info['pid'] == current_pid:
                continue
            cmd_str = ' '.join(cmdline)
            if any(p in cmd_str for p in patterns):
                print(f"Terminating PID={proc.info['pid']} cmd={cmd_str[:80]}")
                proc.terminate()
                terminated.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    # Wait for processes to exit
    gone, alive = psutil.wait_procs(terminated, timeout=5)
    for p in alive:
        try:
            print(f"Killing unresponsive PID={p.pid}")
            p.kill()
        except Exception:
            pass
    print(f"Workers terminated: {len(terminated)}")

def step2_verify_no_stale_workers():
    print("\n--- 2. VERIFY NO STALE WORKERS ---")
    current_pid = os.getpid()
    patterns = ['worker_watchdog.py', 'unified_worker.py', 'start_cluster.py']
    active = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info.get('cmdline')
            if not cmdline or proc.info['pid'] == current_pid:
                continue
            cmd_str = ' '.join(cmdline)
            if any(p in cmd_str for p in patterns):
                active.append((proc.info['pid'], cmd_str))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    print(f"Remaining active cluster workers: {len(active)}")
    for pid, cmd in active:
        print(f"  PID {pid}: {cmd}")
    return len(active) == 0

def step3_clean_redis():
    print("\n--- 3. REDIS STALE STATE CLEANUP ---")
    r = redis.Redis(host=os.getenv('REDIS_HOST', 'localhost'), port=int(os.getenv('REDIS_PORT', 6379)), db=0)
    keys = r.keys('*')
    print(f"Found {len(keys)} keys before cleanup.")
    if keys:
        r.flushdb()
        print("Redis DB flushed clean.")
    print(f"Keys after cleanup: {len(r.keys('*'))}")

def step4_and_5_check_and_purge_sqs():
    print("\n--- 4 & 5. SQS PURGE AND DLQ CHECK ---")
    sqs = boto3.client(
        'sqs',
        region_name=os.getenv('AWS_REGION', 'ap-south-1'),
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
    )
    roles = ['ingestion', 'ai', 'assembly', 'finalize', 'export', 'materialization']
    for role in roles:
        url = queue_service._get_queue_url(role)
        try:
            attrs = sqs.get_queue_attributes(
                QueueUrl=url,
                AttributeNames=['ApproximateNumberOfMessages', 'ApproximateNumberOfMessagesNotVisible', 'ApproximateNumberOfMessagesDelayed']
            )['Attributes']
            total = int(attrs['ApproximateNumberOfMessages']) + int(attrs['ApproximateNumberOfMessagesNotVisible']) + int(attrs['ApproximateNumberOfMessagesDelayed'])
            print(f"Queue {role} ({url}): visible={attrs['ApproximateNumberOfMessages']} invis={attrs['ApproximateNumberOfMessagesNotVisible']} delayed={attrs['ApproximateNumberOfMessagesDelayed']}")
            if total > 0:
                print(f"Purging queue {role}...")
                try:
                    sqs.purge_queue(QueueUrl=url)
                    print(f"Purged {role}")
                except Exception as pe:
                    print(f"Purge error (draining via receive): {pe}")
                    # Drain manually
                    while True:
                        resp = sqs.receive_message(QueueUrl=url, MaxNumberOfMessages=10, WaitTimeSeconds=1)
                        msgs = resp.get('Messages', [])
                        if not msgs:
                            break
                        for m in msgs:
                            sqs.delete_message(QueueUrl=url, ReceiptHandle=m['ReceiptHandle'])
                        print(f"Drained {len(msgs)} messages from {role}")
        except Exception as e:
            print(f"Error checking queue {role}: {e}")

    dlq_urls = [
        os.getenv('SQS_DLQ_QUEUE_URL'),
        os.getenv('SQS_DLQ_QUEUE_URL', '') + '-' + os.getenv('CLUSTER_ENV', 'local'),
        os.getenv('SQS_POISON_QUEUE_URL'),
        os.getenv('SQS_POISON_QUEUE_URL', '') + '-' + os.getenv('CLUSTER_ENV', 'local')
    ]
    for dlq in set(filter(None, dlq_urls)):
        try:
            attrs = sqs.get_queue_attributes(
                QueueUrl=dlq,
                AttributeNames=['ApproximateNumberOfMessages', 'ApproximateNumberOfMessagesNotVisible', 'ApproximateNumberOfMessagesDelayed']
            )['Attributes']
            print(f"DLQ ({dlq}): visible={attrs['ApproximateNumberOfMessages']} invis={attrs['ApproximateNumberOfMessagesNotVisible']}")
        except Exception as e:
            print(f"DLQ check error ({dlq}): {e}")

def step6_verify_db():
    print("\n--- 6. VERIFY DATABASE CONNECTIVITY ---")
    conn = connections['default']
    conn.ensure_connection()
    print(f"Database connected: {conn.is_usable()} (Vendor: {conn.vendor}, DB: {conn.settings_dict.get('NAME')})")

def step7_verify_storage():
    print("\n--- 7. VERIFY STORAGE CONNECTIVITY ---")
    from vouchers.pipeline import storage
    print(f"Storage backend: {'S3' if storage.USE_S3 else 'LOCAL'} (Local root: {getattr(storage, 'LOCAL_STORAGE_ROOT', 'media')})")

def step8_verify_ai():
    print("\n--- 8. VERIFY MISTRAL OCR AVAILABILITY ---")
    from core.ai_proxy import validate_ai_on_startup
    res = validate_ai_on_startup()
    print(f"Mistral OCR Endpoint Status: {'READY' if res else 'FAILED'}")

def step9_verify_env():
    print("\n--- 9. VERIFY REQUIRED ENV VARS ---")
    required = [
        'CLUSTER_ENV', 'MISTRAL_API_KEY', 'REDIS_HOST', 'REDIS_PORT',
        'SQS_INGESTION_QUEUE_URL', 'SQS_AI_QUEUE_URL', 'SQS_ASSEMBLY_QUEUE_URL',
        'SQS_FINALIZE_QUEUE_URL', 'SQS_EXPORT_QUEUE_URL', 'SQS_MATERIALIZATION_QUEUE_URL',
        'AWS_REGION', 'AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY'
    ]
    all_ok = True
    for var in required:
        val = os.getenv(var)
        status = 'SET' if val else 'MISSING'
        if not val:
            all_ok = False
        print(f"  {var}: {status}")
    print(f"All required env vars valid: {all_ok}")

if __name__ == '__main__':
    step1_stop_workers()
    step2_verify_no_stale_workers()
    step3_clean_redis()
    step4_and_5_check_and_purge_sqs()
    step6_verify_db()
    step7_verify_storage()
    step8_verify_ai()
    step9_verify_env()
    print("\n=== CLEAN-ROOM PREPARATION COMPLETE ===")
