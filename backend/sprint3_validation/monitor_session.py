#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Session Monitor: Wait for an entire session to converge to terminal state.

Usage:
  python manage.py shell -c "exec(open('sprint3_validation/monitor_session.py').read())"

Or pass SESSION_ID env var.
"""
import os
import sys
import time
import json

SESSION_ID = os.environ.get("SESSION_ID", "fd6a3d24-8bf5-446a-87f1-13971028e70b")
POLL_TIMEOUT_S = 1800   # 30 minutes
POLL_INTERVAL_S = 5

TERMINAL_STATUSES = {"FINALIZED", "FAILED", "ASSEMBLY_ABORTED", "ERROR", "CANCELLED"}

from ocr_pipeline.models import InvoiceTempOCR

print(f"\n{'='*60}")
print(f"SESSION MONITOR: {SESSION_ID}")
print(f"Timeout: {POLL_TIMEOUT_S//60} minutes, check every {POLL_INTERVAL_S}s")
print(f"{'='*60}")

deadline = time.time() + POLL_TIMEOUT_S
poll_count = 0
prev_summary = {}

while time.time() < deadline:
    records = InvoiceTempOCR.objects.filter(upload_session_id=SESSION_ID).values("id", "status")
    statuses = {r["id"]: r["status"] for r in records}
    total = len(statuses)

    if total == 0:
        print(f"  [{poll_count}] No records found for session {SESSION_ID}. Waiting...")
        time.sleep(POLL_INTERVAL_S)
        poll_count += 1
        continue

    from collections import Counter
    summary = Counter(statuses.values())
    terminal_count = sum(summary.get(s, 0) for s in TERMINAL_STATUSES)
    finalized = summary.get("FINALIZED", 0)
    failed = summary.get("FAILED", 0) + summary.get("ASSEMBLY_ABORTED", 0) + summary.get("ERROR", 0)

    # Print whenever status changes or every 12 polls (~60s)
    if summary != prev_summary or poll_count % 12 == 0:
        elapsed = int(time.time() - (deadline - POLL_TIMEOUT_S))
        print(f"\n  [{elapsed:>4}s] progress={terminal_count}/{total} terminal  "
              f"(FINALIZED={finalized} FAILED={failed})")
        for status, count in sorted(summary.items()):
            print(f"    {status:<20}: {count}")

        # Print non-terminal records
        non_terminal = {rid: st for rid, st in statuses.items() if st not in TERMINAL_STATUSES}
        if non_terminal and len(non_terminal) <= 10:
            print(f"  Non-terminal records:")
            for rid, st in sorted(non_terminal.items()):
                print(f"    record={rid} status={st}")
        prev_summary = Counter(summary)

    if terminal_count >= total:
        print(f"\n{'='*60}")
        print(f"SESSION COMPLETE! All {total} records terminal.")
        print(f"  FINALIZED: {finalized}")
        print(f"  FAILED:    {failed}")
        print(f"  SUCCESS RATE: {finalized/total*100:.1f}%")
        print(f"{'='*60}")
        break

    time.sleep(POLL_INTERVAL_S)
    poll_count += 1
else:
    print(f"\n[TIMEOUT] Session did not converge within {POLL_TIMEOUT_S//60} minutes.")
    from collections import Counter
    records = InvoiceTempOCR.objects.filter(upload_session_id=SESSION_ID).values("id", "status")
    statuses = {r["id"]: r["status"] for r in records}
    summary = Counter(statuses.values())
    print("Final status summary:", dict(summary))
