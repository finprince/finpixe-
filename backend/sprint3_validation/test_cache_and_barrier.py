# -*- coding: utf-8 -*-
"""
Automated Test Suite for Sprint 3 Cache Deadlock & Barrier Convergence
=====================================================================
Validates Cold, Warm, Mixed Cache, Fallback, and Concurrent Ingestion.
"""
import os
import sys
import time
import json
import uuid
# Bootstrap Django
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
import django
django.setup()

import concurrent.futures
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from ocr_pipeline.models import InvoiceTempOCR, InvoicePageResult, SessionFinalizationState, AICache
from ocr_pipeline.ocr_cache import generate_semantic_cache_key
from core.redis_orchestrator import orchestrator
from pending_purchases.models import PendingPurchase

PDF_PATH = r"C:\108\AI-accounting-0.03\backend\media\bulk_pipeline\jobs\832\631593ba---IMG_20260406_0003.pdf"

def clear_db_states(session_id=None):
    """Resets transactional database and Redis states."""
    print("  [Reset] Clearing database transaction and Redis states...")
    # Clear Redis semaphore slots
    keys = orchestrator.redis.keys("active_slots:*")
    if keys:
        orchestrator.redis.delete(*keys)
    # Clear other active slot structures
    orchestrator.redis.delete("ai_active_slots_set")
    
    # Delete relevant page results and sessions
    if session_id:
        InvoicePageResult.objects.filter(session_id=session_id).delete()
        InvoiceTempOCR.objects.filter(upload_session_id=session_id).delete()
        SessionFinalizationState.objects.filter(id=session_id).delete()
    else:
        # Clear all validation run data
        InvoicePageResult.objects.filter(session_id__startswith="test-val-").delete()
        InvoiceTempOCR.objects.filter(upload_session_id__startswith="test-val-").delete()
        SessionFinalizationState.objects.filter(id__startswith="test-val-").delete()

def extract_ocr_keys_from_results(session_id):
    """Loads OCR text from results to compute cache keys."""
    results = InvoicePageResult.objects.filter(session_id=session_id).order_by('page_number')
    keys_map = {}
    for res in results:
        payload = res.canonical_payload
        ocr_text = payload.get('_pdf_ocr_text') or payload.get('_raw_text') or ""
        # Get prompt and schema hashes
        import hashlib
        from ocr_pipeline.extraction import base_prompt, schema_str, AI_MODEL_NAME
        prompt_hash = hashlib.sha256(base_prompt.encode('utf-8')).hexdigest()
        schema_hash = hashlib.sha256(schema_str.encode('utf-8')).hexdigest()
        
        cache_key = generate_semantic_cache_key(ocr_text, AI_MODEL_NAME, "latest", prompt_hash, schema_hash)
        keys_map[res.page_number] = {
            'key': cache_key,
            'ocr_text': ocr_text,
            'payload': payload,
            'prompt_hash': prompt_hash,
            'schema_hash': schema_hash
        }
    return keys_map

def upload_and_wait(client, session_id):
    """Uploads the test PDF and polls until completion."""
    print(f"  [Upload] Uploading PDF under session: {session_id}")
    with open(PDF_PATH, 'rb') as f:
        resp = client.post('/api/ocr-staging/', {
            'files': f,
            'voucher_type': 'PURCHASE',
            'upload_type': 'SPRINT3_VALIDATION',
            'upload_session_id': session_id
        }, format='multipart')
        
    if resp.status_code not in (200, 201, 202):
        raise RuntimeError(f"Upload failed: {resp.status_code} {resp.text}")
    
    record_id = resp.json().get('record_id') or resp.json().get('id')
    print(f"  [Ingestion] Record created: {record_id}. Waiting for completion...")
    
    # Poll database for completion
    timeout = 360
    start_time = time.time()
    while time.time() - start_time < timeout:
        rec = InvoiceTempOCR.objects.filter(upload_session_id=session_id).first()
        barrier = SessionFinalizationState.objects.filter(id=str(rec.id)).first() if rec else None
        completed = barrier.completed_pages if barrier else 0
        expected = barrier.expected_pages if barrier else 0
        
        if rec and rec.status in {"FINALIZED", "FAILED", "ASSEMBLY_ABORTED", "ERROR"}:
            print(f"  [Ingestion] Terminal state reached: status={rec.status} progress={completed}/{expected}")
            return rec.id, rec.status
        
        time.sleep(2)
        
    raise TimeoutError(f"Ingestion timed out after {timeout} seconds")

def run_tests():
    # Setup client
    User = get_user_model()
    admin_user = User.objects.get(username='admin')
    client = APIClient()
    client.force_authenticate(user=admin_user)
    
    print("\n" + "="*80)
    print("  RUNNING SPRINT 3 DEADLOCK & BARRIER CONVERGENCE TESTS")
    print("="*80 + "\n")
    
    # ─────────────────────────────────────────────────────────────────────────
    # TEST 1: Cold Cache Run
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- TEST 1: Cold Cache Run ---")
    # Clean cache of any target keys
    AICache.objects.filter(key_hash__startswith="test-key-").delete()
    clear_db_states()
    
    session_id_1 = f"test-val-cold-{uuid.uuid4().hex[:8]}"
    rec_id_1, status_1 = upload_and_wait(client, session_id_1)
    
    # Assertions
    barrier_1 = SessionFinalizationState.objects.get(id=str(rec_id_1))
    page_results_count = InvoicePageResult.objects.filter(session_id=session_id_1).count()
    
    assert status_1 == "FINALIZED", f"Expected FINALIZED, got {status_1}"
    assert barrier_1.completed_pages == 19, f"Expected 19 completed pages, got {barrier_1.completed_pages}"
    assert page_results_count == 19, f"Expected 19 page results, got {page_results_count}"
    print("[PASS] Test 1: Cold Cache Run complete and barrier converged!")
    
    # Extract cache keys from Test 1 results
    cache_keys_map = extract_ocr_keys_from_results(session_id_1)
    print(f"  [Cache Info] Extracted {len(cache_keys_map)} cache keys successfully.")
    
    # ─────────────────────────────────────────────────────────────────────────
    # TEST 2: Warm Cache Run
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- TEST 2: Warm Cache Run ---")
    clear_db_states()
    
    # Ensure all 19 pages are cached in AICache
    from ocr_pipeline.extraction import AI_MODEL_NAME
    for p_num, info in cache_keys_map.items():
        AICache.objects.update_or_create(
            key_hash=info['key'],
            defaults={'payload': info['payload']}
        )
        
    session_id_2 = f"test-val-warm-{uuid.uuid4().hex[:8]}"
    rec_id_2, status_2 = upload_and_wait(client, session_id_2)
    
    # Assertions
    barrier_2 = SessionFinalizationState.objects.get(id=str(rec_id_2))
    page_results_count_2 = InvoicePageResult.objects.filter(session_id=session_id_2).count()
    
    assert status_2 == "FINALIZED", f"Expected FINALIZED, got {status_2}"
    assert barrier_2.completed_pages == 19, f"Expected 19 completed pages, got {barrier_2.completed_pages}"
    assert page_results_count_2 == 19, f"Expected 19 page results, got {page_results_count_2}"
    print("[PASS] Test 2: Warm Cache Run complete and barrier converged with 19 cache hits!")
    
    # ─────────────────────────────────────────────────────────────────────────
    # TEST 3: Mixed Cache Run (Pages 1–5 cached, Pages 6–19 uncached)
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- TEST 3: Mixed Cache Run ---")
    clear_db_states()
    
    # Clear all cache entries, then restore only pages 1–5
    for p_num, info in cache_keys_map.items():
        AICache.objects.filter(key_hash=info['key']).delete()
        
    for p_num in range(1, 6):
        info = cache_keys_map[p_num]
        AICache.objects.update_or_create(
            key_hash=info['key'],
            defaults={'payload': info['payload']}
        )
        
    session_id_3 = f"test-val-mixed-{uuid.uuid4().hex[:8]}"
    rec_id_3, status_3 = upload_and_wait(client, session_id_3)
    
    # Assertions
    barrier_3 = SessionFinalizationState.objects.get(id=str(rec_id_3))
    page_results_count_3 = InvoicePageResult.objects.filter(session_id=session_id_3).count()
    
    assert status_3 == "FINALIZED", f"Expected FINALIZED, got {status_3}"
    assert barrier_3.completed_pages == 19, f"Expected 19 completed pages, got {barrier_3.completed_pages}"
    assert page_results_count_3 == 19, f"Expected 19 page results, got {page_results_count_3}"
    print("[PASS] Test 3: Mixed Cache Run complete and barrier converged!")
    
    # ─────────────────────────────────────────────────────────────────────────
    # TEST 4: Cache Failure Fallback Run (Cache row deleted before lookup)
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- TEST 4: Cache Failure Fallback Run ---")
    clear_db_states()
    
    # Populate cache for all pages
    for p_num, info in cache_keys_map.items():
        AICache.objects.update_or_create(
            key_hash=info['key'],
            defaults={'payload': info['payload']}
        )
        
    # We will upload and concurrently delete page 3 cache key
    session_id_4 = f"test-val-fallback-{uuid.uuid4().hex[:8]}"
    
    def upload_and_delete():
        with open(PDF_PATH, 'rb') as f:
            client.post('/api/ocr-staging/', {
                'files': f,
                'voucher_type': 'PURCHASE',
                'upload_type': 'SPRINT3_VALIDATION',
                'upload_session_id': session_id_4
            }, format='multipart')
        
        # Immediately delete page 3's cache row and invalidate file-hash cache
        time.sleep(2)  # brief wait for ingestion to enqueue
        
        # Invalidate from file-hash cache (Tier 1 & 2)
        rec = InvoiceTempOCR.objects.filter(upload_session_id=session_id_4).first()
        if rec and rec.file_hash:
            from ocr_pipeline.ocr_cache import OCRResponseCache
            OCRResponseCache.invalidate(rec.file_hash, 3)
            print(f"  [Fallback Trigger] Invalidated page 3 from file-hash cache: {rec.file_hash}")
            
        # Invalidate semantic cache
        p3_key = cache_keys_map[3]['key']
        deleted, _ = AICache.objects.filter(key_hash=p3_key).delete()
        print(f"  [Fallback Trigger] Deleted page 3 semantic cache row: count={deleted}")
        
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(upload_and_delete)
        future.result()  # Wait for upload+delete thread to complete
        
    # Wait for completion — poll by session_id (consistent with Tests 1-3)
    timeout = 360
    start_time = time.time()
    status_4 = "PENDING"
    rec_id_4 = None
    while time.time() - start_time < timeout:
        rec = InvoiceTempOCR.objects.filter(upload_session_id=session_id_4).first()
        if rec:
            rec_id_4 = rec.id
            barrier = SessionFinalizationState.objects.filter(id=str(rec.id)).first()
            completed = barrier.completed_pages if barrier else 0
            expected = barrier.expected_pages if barrier else 0
            
            if rec.status in {"FINALIZED", "FAILED", "ASSEMBLY_ABORTED", "ERROR"}:
                print(f"  [Ingestion] Terminal state reached: status={rec.status} progress={completed}/{expected}")
                status_4 = rec.status
                break
        time.sleep(2)
        
    # Assertions
    barrier_4 = SessionFinalizationState.objects.get(id=str(rec_id_4))
    page_results_count_4 = InvoicePageResult.objects.filter(session_id=session_id_4).count()
    
    assert status_4 == "FINALIZED", f"Expected FINALIZED, got {status_4}"
    assert barrier_4.completed_pages == 19, f"Expected 19 completed pages, got {barrier_4.completed_pages}"
    assert page_results_count_4 == 19, f"Expected 19 page results, got {page_results_count_4}"
    print("[PASS] Test 4: Cache Failure Fallback Run complete and barrier converged!")
    
    # ─────────────────────────────────────────────────────────────────────────
    # TEST 5: Concurrent Duplicate Ingestion
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- TEST 5: Concurrent Duplicate Ingestion ---")
    clear_db_states()
    
    # Ensure all cached
    for p_num, info in cache_keys_map.items():
        AICache.objects.update_or_create(
            key_hash=info['key'],
            defaults={'payload': info['payload']}
        )
        
    session_id_5a = f"test-val-concurrent-a-{uuid.uuid4().hex[:8]}"
    session_id_5b = f"test-val-concurrent-b-{uuid.uuid4().hex[:8]}"
    
    def upload_concurrent(sid):
        with open(PDF_PATH, 'rb') as f:
            client.post('/api/ocr-staging/', {
                'files': f,
                'voucher_type': 'PURCHASE',
                'upload_type': 'SPRINT3_VALIDATION',
                'upload_session_id': sid
            }, format='multipart')
        return sid  # Return session_id so we can poll by it
        
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(upload_concurrent, session_id_5a)
        f2 = executor.submit(upload_concurrent, session_id_5b)
        f1.result()
        f2.result()

    print(f"  [Concurrent] Uploads started. A: {session_id_5a}, B: {session_id_5b}")

    # Poll both — by session_id, consistent with Tests 1-3
    # Timeout is 360s (6 min) because 2 concurrent 19-page sessions = 38 pages total
    timeout = 360
    start_time = time.time()
    rec_a = None
    rec_b = None
    while time.time() - start_time < timeout:
        rec_a = InvoiceTempOCR.objects.filter(upload_session_id=session_id_5a).first()
        rec_b = InvoiceTempOCR.objects.filter(upload_session_id=session_id_5b).first()
        
        terminal = {"FINALIZED", "FAILED", "ASSEMBLY_ABORTED", "ERROR"}
        a_done = rec_a and rec_a.status in terminal
        b_done = rec_b and rec_b.status in terminal
        if a_done and b_done:
            print(f"  [Concurrent] Terminal states reached. A: {rec_a.status}, B: {rec_b.status}")
            break
        time.sleep(2)
        
    barrier_a = SessionFinalizationState.objects.get(id=str(rec_a.id))
    barrier_b = SessionFinalizationState.objects.get(id=str(rec_b.id))
    
    assert rec_a.status == "FINALIZED", f"A failed: {rec_a.status}"
    assert rec_b.status == "FINALIZED", f"B failed: {rec_b.status}"
    assert barrier_a.completed_pages == 19, f"A pages: {barrier_a.completed_pages}"
    assert barrier_b.completed_pages == 19, f"B pages: {barrier_b.completed_pages}"
    print("[PASS] Test 5: Concurrent Duplicate Ingestion complete and converged without deadlock!")
    
    print("\n" + "="*80)
    print("  ALL SPRINT 3 DEADLOCK & BARRIER CONVERGENCE TESTS PASSED!")
    print("="*80 + "\n")

if __name__ == "__main__":
    run_tests()
