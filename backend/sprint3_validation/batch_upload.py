# -*- coding: utf-8 -*-
"""
Phase 2: Batch Upload Orchestrator
====================================
Uploads all 22 invoices through the production API (CleanOCRStagingView).
Authenticates via JWT, polls session status until terminal, and records
per-file outcomes.

Amendment 4: Continues on failure — never stops mid-batch.
No source code modifications. Read-only observer.
"""
import os
import sys
import json
import time
import uuid
import requests
from datetime import datetime, timezone

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

# Initialize Django before any model imports
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
try:
    import django
    django.setup()
except RuntimeError:
    pass  # Already configured (e.g., when run inside a management command)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "reports")
os.makedirs(OUTPUT_DIR, exist_ok=True)

INVOICE_DIR = r"C:\Users\ulaganathan\Downloads\New folder (2)"
SUPPORTED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".tiff", ".tif"}

# API config
API_BASE = os.getenv("VALIDATION_API_BASE", "http://localhost:8000")
VALIDATION_USER = os.getenv("VALIDATION_USER", "admin")
VALIDATION_EMAIL = os.getenv("VALIDATION_EMAIL", "admin@budstech.com")
VALIDATION_PASS = os.getenv("VALIDATION_PASS", "admin123")

# Max time to wait for the ENTIRE SESSION to complete (all invoices)
SESSION_POLL_TIMEOUT_S = 1800  # 30 minutes for a full 23-invoice batch
SESSION_POLL_INTERVAL_S = 5    # Check every 5 seconds



def load_manifest() -> dict:
    manifest_path = os.path.join(OUTPUT_DIR, "REAL_BATCH_MANIFEST.json")
    if not os.path.isfile(manifest_path):
        print("[ERROR] REAL_BATCH_MANIFEST.json not found. Run generate_manifest.py first.")
        sys.exit(1)
    with open(manifest_path, encoding="utf-8") as f:
        return json.load(f)


def get_session_id() -> str:
    sid_path = os.path.join(OUTPUT_DIR, "SESSION_ID.txt")
    if os.path.isfile(sid_path):
        with open(sid_path) as f:
            return f.read().strip()
    return str(uuid.uuid4())


def authenticate(session: requests.Session) -> str:
    """Obtain JWT token and attach to session. Returns token string."""
    user = os.getenv("VALIDATION_USER", VALIDATION_USER)
    email = os.getenv("VALIDATION_EMAIL", VALIDATION_EMAIL)
    passwd = os.getenv("VALIDATION_PASS", VALIDATION_PASS)

    if not user or not passwd:
        raise RuntimeError(
            "Authentication credentials required.\n"
            "Set VALIDATION_USER, VALIDATION_EMAIL and VALIDATION_PASS env vars.\n"
            "Example:\n"
            "  $env:VALIDATION_USER='admin'\n"
            "  $env:VALIDATION_EMAIL='admin@budstech.com'\n"
            "  $env:VALIDATION_PASS='Sprint3Val@2026'"
        )

    # The login endpoint requires username + email + password
    login_url = f"{API_BASE}/api/auth/login/"
    payload = {"username": user, "email": email, "password": passwd}
    resp = session.post(login_url, json=payload, timeout=30)
    if resp.status_code == 429:
        raise RuntimeError(
            f"Login rate-limited (429). Wait 5 minutes and retry.\n{resp.text[:200]}"
        )
    if resp.status_code != 200:
        raise RuntimeError(f"Login failed [{resp.status_code}]: {resp.text[:300]}")

    data = resp.json()
    token = data.get("access") or data.get("token")
    if not token:
        raise RuntimeError(f"No token in login response: {list(data.keys())}")

    session.headers.update({"Authorization": f"Bearer {token}"})
    print(f"  [Auth] Authenticated as {user} ({email})")
    return token


def upload_invoice(session: requests.Session, file_entry: dict, upload_session_id: str) -> dict:
    """Upload a single invoice file and return the response dict."""
    fpath = file_entry["file_path"]
    fname = file_entry["filename"]
    mime = "application/pdf" if fname.lower().endswith(".pdf") else "image/jpeg"

    url = f"{API_BASE}/api/ocr-staging/"
    t_start = time.time()

    with open(fpath, "rb") as f:
        files = [("files", (fname, f, mime))]
        data = {
            "voucher_type": "PURCHASE",
            "upload_type": "SPRINT3_VALIDATION",
            "upload_session_id": upload_session_id,
        }
        try:
            resp = session.post(url, files=files, data=data, timeout=120)
            elapsed = round(time.time() - t_start, 2)
            if resp.status_code in (200, 201, 202):
                try:
                    result = resp.json()
                except Exception:
                    result = {"raw": resp.text[:200]}
                return {
                    "filename": fname,
                    "upload_status": "OK",
                    "http_status": resp.status_code,
                    "job_id": result.get("job_id") or result.get("id"),
                    "record_id": result.get("record_id") or result.get("id"),
                    "upload_elapsed_s": elapsed,
                    "response": result,
                }
            else:
                return {
                    "filename": fname,
                    "upload_status": "HTTP_ERROR",
                    "http_status": resp.status_code,
                    "error": resp.text[:500],
                    "upload_elapsed_s": elapsed,
                }
        except Exception as e:
            return {
                "filename": fname,
                "upload_status": "EXCEPTION",
                "error": str(e)[:300],
                "upload_elapsed_s": round(time.time() - t_start, 2),
            }


def wait_for_session_completion(session_id: str, record_ids: list[str]) -> dict:
    """Wait for ALL uploaded invoice records to reach a terminal state.
    
    DESIGN RATIONALE:
    The finalize_worker uses a session-level barrier that requires ALL invoices
    in a session to complete before finalizing any. Sequential upload + per-invoice
    polling causes a deadlock. This function uploads everything first, then waits
    for the session to converge as a whole.
    
    Terminal statuses: FINALIZED, FAILED, ASSEMBLY_ABORTED, ERROR, CANCELLED
    """
    from ocr_pipeline.models import InvoiceTempOCR
    TERMINAL_STATUSES = {"FINALIZED", "FAILED", "ASSEMBLY_ABORTED", "ERROR", "CANCELLED"}

    deadline = time.time() + SESSION_POLL_TIMEOUT_S
    poll_count = 0
    total_records = len(record_ids)

    print(f"\n  Waiting for session {session_id[:8]}... ({total_records} records, max {SESSION_POLL_TIMEOUT_S//60} min)")

    while time.time() < deadline:
        try:
            statuses = dict(
                InvoiceTempOCR.objects
                .filter(id__in=record_ids)
                .values_list('id', 'status')
            )
            terminal_count = sum(1 for s in statuses.values() if s in TERMINAL_STATUSES)
            finalized_count = sum(1 for s in statuses.values() if s == 'FINALIZED')
            failed_count = sum(1 for s in statuses.values() if s in {'FAILED', 'ASSEMBLY_ABORTED', 'ERROR'})

            if poll_count % 12 == 0:  # Print every 60s
                print(f"  Session progress: {terminal_count}/{total_records} terminal "
                      f"(FINALIZED={finalized_count} FAILED={failed_count})")
                # Print status of all non-terminal records
                for rid, st in sorted(statuses.items()):
                    if st not in TERMINAL_STATUSES:
                        print(f"    record={rid} status={st}")

            if terminal_count >= total_records:
                print(f"  All {total_records} records terminal! FINALIZED={finalized_count} FAILED={failed_count}")
                # Return per-record outcomes
                return {
                    "final_statuses": dict(statuses),
                    "terminal": True,
                    "poll_count": poll_count,
                    "finalized_count": finalized_count,
                    "failed_count": failed_count,
                }
        except Exception as e:
            if poll_count % 12 == 0:
                print(f"  Session poll error: {e}")

        time.sleep(SESSION_POLL_INTERVAL_S)
        poll_count += 1

    # Timeout — gather final statuses
    try:
        statuses = dict(
            InvoiceTempOCR.objects
            .filter(id__in=record_ids)
            .values_list('id', 'status')
        )
    except Exception:
        statuses = {}

    return {
        "final_statuses": statuses,
        "terminal": False,
        "poll_count": poll_count,
        "finalized_count": sum(1 for s in statuses.values() if s == 'FINALIZED'),
        "failed_count": sum(1 for s in statuses.values() if s in {'FAILED', 'ASSEMBLY_ABORTED', 'ERROR'}),
    }


def run_batch_upload():
    print(f"\n{'='*60}")
    print("SPRINT 3 — PHASE 2: BATCH UPLOAD")
    print(f"{'='*60}")

    manifest = load_manifest()
    batch_session_id = manifest["session_id"]
    invoice_files = manifest["files"]

    print(f"Batch session ID : {batch_session_id}")
    print(f"Total invoices   : {len(invoice_files)}")
    print(f"API Base         : {API_BASE}")
    print()

    session = requests.Session()

    # Authenticate
    print("[AUTH] Logging in ...")
    try:
        authenticate(session)
    except RuntimeError as e:
        print(f"\n[FATAL] {e}")
        sys.exit(1)
    print()

    results = []
    record_map = {}   # filename -> record_id
    job_map = {}      # filename -> job_id
    success_count = 0
    failure_count = 0

    # ── PHASE 1: FIRE-AND-FORGET UPLOAD ALL INVOICES ──
    # Upload all invoices without waiting between them.
    # The finalize_worker uses a session-level barrier requiring ALL invoices
    # to complete before finalizing any. Sequential polling deadlocks.
    print(f"\n{'-'*60}")
    print("PHASE 1: Uploading all invoices (fire-and-forget)")
    print(f"{'-'*60}")

    for i, entry in enumerate(invoice_files, 1):
        fname = entry["filename"]
        print(f"[{i:02d}/{len(invoice_files)}] Uploading: {fname}")

        # Re-authenticate every 4 uploads to prevent SimpleJWT token expiration (5 min limit)
        # but avoid hitting the login rate limiter (429 throttle).
        if i == 1 or i % 4 == 1:
            try:
                authenticate(session)
            except Exception as auth_err:
                print(f"  [WARN] Re-authentication skipped: {auth_err}. Retrying with existing token.")

        upload_result = upload_invoice(session, entry, batch_session_id)
        upload_status = upload_result.get("upload_status", "UNKNOWN")
        print(f"  Upload: {upload_status} (HTTP {upload_result.get('http_status', '-')}) "
              f"in {upload_result.get('upload_elapsed_s', '?')}s")

        job_id = upload_result.get("job_id", "")
        record_id = ""
        if upload_status == "OK" and job_id:
            try:
                from ocr_pipeline.models import OCRTask
                # Wait briefly for the OCRTask to be created
                time.sleep(1)
                task = OCRTask.objects.filter(job_id=job_id, result_id__isnull=False).first()
                if task and task.result_id:
                    record_id = str(task.result_id)
                    print(f"  record_id={record_id}")
                else:
                    time.sleep(2)
                    task = OCRTask.objects.filter(job_id=job_id, result_id__isnull=False).first()
                    if task and task.result_id:
                        record_id = str(task.result_id)
                        print(f"  record_id={record_id} (retry)")
            except Exception as te:
                print(f"  [WARN] Could not resolve record_id: {te}")

        record_map[fname] = record_id
        job_map[fname] = job_id
        results.append({
            "index": i,
            "filename": fname,
            "file_hash": entry["file_hash_sha256"],
            "page_count": entry["page_count"],
            "upload": upload_result,
            "record_id": record_id,
            "pipeline": {},  # filled in PHASE 2
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        if upload_status != "OK":
            failure_count += 1
            print(f"  [WARN] Upload failed: {upload_status}")

        print()

    # ── PHASE 2: WAIT FOR WHOLE SESSION TO CONVERGE ──
    all_record_ids = [r for r in record_map.values() if r]
    print(f"\n{'-'*60}")
    print(f"PHASE 2: Waiting for session {batch_session_id[:8]}... to converge")
    print(f"  Tracking {len(all_record_ids)} record IDs across {len(invoice_files)} invoices")
    print(f"{'-'*60}")

    if all_record_ids:
        session_result = wait_for_session_completion(batch_session_id, all_record_ids)
        final_statuses = session_result.get("final_statuses", {})
        success_count = session_result.get("finalized_count", 0)
        # Failed = records that are terminal but not FINALIZED + uploads that had no record_id
        terminal_failed = session_result.get("failed_count", 0)
        no_record_failed = sum(1 for fname, rid in record_map.items() if not rid
                               and any(r["filename"] == fname and r["upload"]["upload_status"] == "OK"
                                       for r in results))
        failure_count += terminal_failed + no_record_failed

        # Annotate per-file results with final status
        for result in results:
            rid = result.get("record_id", "")
            if rid:
                result["pipeline"] = {
                    "final_status": final_statuses.get(int(rid), "UNKNOWN"),
                    "terminal": True,
                    "poll_count": session_result.get("poll_count", 0),
                }
            elif result["upload"]["upload_status"] == "OK":
                result["pipeline"] = {"final_status": "NO_RECORD_ID", "terminal": False, "poll_count": 0}
    else:
        print("  [WARN] No record IDs resolved. Session wait skipped.")
        session_result = {"terminal": False, "finalized_count": 0, "failed_count": 0, "poll_count": 0}

    # Write results
    batch_results = {
        "session_id": batch_session_id,
        "total_invoices": len(invoice_files),
        "success_count": success_count,
        "failure_count": failure_count,
        "success_rate_pct": round(success_count / len(invoice_files) * 100, 1),
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "results": results,
    }

    out_path = os.path.join(OUTPUT_DIR, "BATCH_UPLOAD_RESULTS.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(batch_results, f, indent=2, ensure_ascii=False)

    print(f"{'='*60}")
    print(f"BATCH UPLOAD COMPLETE")
    print(f"  Total    : {len(invoice_files)}")
    print(f"  Success  : {success_count}")
    print(f"  Failures : {failure_count}")
    print(f"  Rate     : {batch_results['success_rate_pct']}%")
    print(f"  Results  : {out_path}")

    return batch_results


if __name__ == "__main__":
    run_batch_upload()
