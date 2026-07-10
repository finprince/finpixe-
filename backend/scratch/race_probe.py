"""
FORENSIC RACE PROBE
===================
Hypothesis: The finalize worker reads SessionFinalizationState (snapshot_complete / FinalizedSnapshot)
BEFORE the assembly worker transaction.atomic() in assemble_multi_page_record() commits.

Key race window to prove:
  if [BARRIER_STATE_READ].timestamp < [SNAPSHOT_TX_COMMIT].timestamp -> race PROVEN.
"""
import os, sys, time, json, re, threading, datetime, logging, glob

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d [PROBE] %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger("race_probe")

DJANGO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, DJANGO_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings.local")
import django; django.setup()
import requests

BASE_URL = "http://127.0.0.1:8000"
PDF_PATH = r"C:\Users\ulaganathan\Downloads\New folder (2)\IMG_20260406_0003.pdf"
LOGS_DIR = os.path.join(DJANGO_DIR, "logs")

EVENTS_OF_INTEREST = [
    "SNAPSHOT_TX_ENTER",
    "SNAPSHOT_ROW_CREATED",
    "SNAPSHOT_COMPLETE_SET",
    "SNAPSHOT_TX_COMMIT",
    "FINALIZE_ENQUEUE_START",
    "ONE_SHOT_FINALIZE_CONFIRMED",
    "CANONICAL_BARRIER_REACHED",
    "BARRIER_STATE_WRITE",
    "FINALIZE_WORKER_START",
    "FINALIZE_STAGE_ENTER",
    "SESSION_AGGREGATE_START",
    "BARRIER_STATE_READ",
    "SNAPSHOT_STATE_READ",
    "SESSION_STATE_AGGREGATE",
    "FINALIZE_BLOCKED_BARRIER",
    "HYDRATION_VISIBILITY_PENDING",
    "FINALIZE_STATE_PERSISTED",
    "FINALIZE_STAGE_EXIT",
]

def get_csrf_token(s):
    r = s.get(f"{BASE_URL}/login/")
    m = re.search(r'csrfmiddlewaretoken.*?value=["\']([^"\']+)', r.text)
    return m.group(1) if m else ""

def authenticate(s):
    csrf = get_csrf_token(s)
    r = s.post(f"{BASE_URL}/login/", data={
        "csrfmiddlewaretoken": csrf,
        "username": "admin@admin.com",
        "password": "admin",
    }, allow_redirects=True)
    assert r.status_code in (200, 302), f"Auth failed {r.status_code}"
    log.info("Auth OK")

def upload_invoice(s, sid):
    with open(PDF_PATH, "rb") as f:
        r = s.post(f"{BASE_URL}/api/ocr/upload/",
            files={"files": (os.path.basename(PDF_PATH), f, "application/pdf")},
            data={"upload_session_id": sid})
    r.raise_for_status()
    return r.json()

def poll_status(s, sid):
    r = s.get(f"{BASE_URL}/api/ocr/session-status/{sid}/")
    return r.json() if r.status_code == 200 else {}

class LogTailer(threading.Thread):
    TS_RE = re.compile(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d+|\d{2}:\d{2}:\d{2}[.,]\d+)")

    def __init__(self, session_id):
        super().__init__(daemon=True)
        self.session_id = str(session_id)
        self.record_id = "PLACEHOLDER"
        self.events = []
        self.lock = threading.Lock()
        self._stop = threading.Event()
        self._seen = set()

    def stop(self): self._stop.set()

    def run(self):
        positions = {}
        while not self._stop.is_set():
            for lf in glob.glob(os.path.join(LOGS_DIR, "*.log")):
                if lf not in positions:
                    try: positions[lf] = os.path.getsize(lf)
                    except: positions[lf] = 0
                try:
                    with open(lf, "r", encoding="utf-8", errors="replace") as fh:
                        fh.seek(positions[lf])
                        data = fh.read()
                        positions[lf] = fh.tell()
                except: continue
                for line in data.splitlines():
                    if self.record_id not in line and self.session_id not in line:
                        continue
                    if line in self._seen: continue
                    self._seen.add(line)
                    for tok in EVENTS_OF_INTEREST:
                        if f"[{tok}]" in line:
                            ts = self._parse_ts(line)
                            with self.lock:
                                self.events.append((ts, tok, line.strip()))
                            log.info(f"  CAPTURE {tok}")
                            break
            time.sleep(0.05)

    def _parse_ts(self, line):
        m = self.TS_RE.search(line)
        if not m: return time.time()
        raw = m.group(1).replace(",", ".")
        for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%H:%M:%S.%f"):
            try:
                dt = datetime.datetime.strptime(raw, fmt)
                if dt.year == 1900:
                    n = datetime.datetime.now()
                    dt = dt.replace(year=n.year, month=n.month, day=n.day)
                return dt.timestamp()
            except: pass
        return time.time()

    def get_events(self):
        with self.lock: return list(self.events)


def query_db_state(record_id, session_id):
    from ocr_pipeline.models import SessionFinalizationState, FinalizedSnapshot
    from django.db import connection
    out = {}
    try:
        sfs = SessionFinalizationState.objects.filter(id=str(record_id)).values(
            "expected_pages","completed_pages","failed_pages",
            "snapshot_created","snapshot_complete","materialization_complete",
            "assembly_complete","ai_complete","status").first()
        out["sfs"] = {k: str(v) for k, v in (sfs or {}).items()}
    except Exception as e: out["sfs_error"] = str(e)
    try:
        out["snapshot_count"] = FinalizedSnapshot.objects.filter(session_id=session_id).count()
    except Exception as e: out["snapshot_count_error"] = str(e)
    try:
        with connection.cursor() as cur:
            cur.execute("SELECT NOW(6)")
            out["mysql_now"] = str(cur.fetchone()[0])
    except Exception as e: out["mysql_now_error"] = str(e)
    return out


def find_first(events, token):
    for ts, tok, line in events:
        if tok == token: return ts, line
    return None, None


def main():
    import uuid
    log.info("=" * 68)
    log.info("FORENSIC RACE PROBE — finalize worker read-before-commit")
    log.info("=" * 68)

    session = requests.Session()
    authenticate(session)
    sid = str(uuid.uuid4())
    log.info(f"Session UUID: {sid}")

    tailer = LogTailer(session_id=sid)
    tailer.start()

    log.info("Uploading...")
    t0_upload = time.time()
    resp = upload_invoice(session, sid)
    log.info(f"Upload: {resp}")

    record_id = None
    for _ in range(30):
        time.sleep(2)
        try:
            st = poll_status(session, sid)
            record_id = st.get("record_id") or st.get("id")
            if record_id: break
        except: pass
    if not record_id:
        log.error("record_id not resolved — abort")
        tailer.stop(); sys.exit(1)

    tailer.record_id = str(record_id)
    log.info(f"record_id={record_id}")

    log.info("Polling...")
    t_start = time.time()
    poll_hist = []
    final_status = None
    while time.time() - t_start < 300:
        time.sleep(3)
        try:
            st = poll_status(session, sid)
            s = st.get("status","?")
            p = float(st.get("progress", 0) or 0)
            rows = st.get("rows", 0)
            ts = time.time()
            log.info(f"  status={s} progress={p:.1f}% rows={rows}")
            entry = {"ts": ts, "status": s, "progress": p, "rows": rows}
            if p >= 99.0 or s in ("FINALIZED", "HYDRATION_READY"):
                entry["db"] = query_db_state(record_id, sid)
                log.info(f"  DB: {entry['db']}")
            poll_hist.append(entry)
            if s in ("FINALIZED","HYDRATION_READY","FAILED","ERROR"):
                final_status = s; break
        except Exception as e: log.warning(f"Poll err: {e}")

    time.sleep(5)
    tailer.stop(); tailer.join(timeout=3)

    events = sorted(tailer.get_events(), key=lambda x: x[0])
    t0 = events[0][0] if events else time.time()

    log.info("")
    log.info("=" * 68)
    log.info("EVENT TIMELINE")
    log.info("=" * 68)
    for ts, tok, line in events:
        rel = (ts - t0) * 1000
        log.info(f"  T+{rel:9.1f}ms  [{tok}]")
        for field in ("expected","completed","failed","snapshot_complete","snapshot_count"):
            m = re.search(rf"{field}=(\S+)", line)
            if m: log.info(f"    {field}={m.group(1)}")

    ts_tx_commit,    _   = find_first(events, "SNAPSHOT_TX_COMMIT")
    ts_barrier_read, bl  = find_first(events, "BARRIER_STATE_READ")
    ts_snap_read,    _   = find_first(events, "SNAPSHOT_STATE_READ")
    ts_fin_start,    _   = find_first(events, "FINALIZE_WORKER_START")
    ts_fin_blocked,  fbl = find_first(events, "FINALIZE_BLOCKED_BARRIER")
    ts_enqueue,      _   = find_first(events, "FINALIZE_ENQUEUE_START")

    log.info("")
    log.info("=" * 68)
    log.info("RACE ANALYSIS")
    log.info("=" * 68)

    def gap(a, b, label):
        if a and b:
            g = (b - a) * 1000
            direction = "AFTER" if g >= 0 else "*** BEFORE ***"
            log.info(f"  {label}: {g:+.1f}ms ({direction} TX commit)")
            return g
        else:
            log.warning(f"  {label}: missing events ({a=} {b=})")
            return None

    g1 = gap(ts_tx_commit, ts_fin_start,    "TX_COMMIT → FINALIZE_WORKER_START")
    g2 = gap(ts_tx_commit, ts_barrier_read, "TX_COMMIT → BARRIER_STATE_READ    ")
    g3 = gap(ts_tx_commit, ts_snap_read,    "TX_COMMIT → SNAPSHOT_STATE_READ   ")

    if ts_fin_blocked:
        log.warning(f"  FINALIZE_BLOCKED_BARRIER fired!")
        m = re.search(r"snapshot_complete=(\S+)", fbl or "")
        if m: log.warning(f"    snapshot_complete seen by finalize worker: {m.group(1)}")
        m2 = re.search(r"expected=(\S+).*completed=(\S+).*failed=(\S+)", fbl or "")
        if m2: log.warning(f"    expected={m2.group(1)} completed={m2.group(2)} failed={m2.group(3)}")

    log.info("")
    log.info("=" * 68)
    log.info("VERDICT")
    log.info("=" * 68)
    race_proven = False
    if g2 is not None and g2 < 0:
        race_proven = True
        log.error("VERDICT: RACE CONDITION PROVEN")
        log.error(f"  BARRIER_STATE_READ occurred {-g2:.1f}ms BEFORE transaction committed.")
    elif ts_fin_blocked and g2 is not None and g2 >= 0:
        log.warning("VERDICT: BLOCKED AFTER TX COMMIT — DIFFERENT DEFECT")
        log.warning("  Finalize read AFTER commit but still saw snapshot_complete=False.")
        log.warning("  This means snapshot_complete is written in a SEPARATE, LATER transaction.")
        log.warning("  Investigate: where/when is SFS.snapshot_complete set to True?")
    elif not ts_fin_blocked and final_status in ("FINALIZED","HYDRATION_READY"):
        log.info("VERDICT: COMPLETED CLEANLY — No race observed this run.")
    else:
        log.warning(f"VERDICT: INCONCLUSIVE (final_status={final_status})")

    out_path = os.path.join(DJANGO_DIR, "scratch", "race_probe_trace.json")
    with open(out_path, "w") as f:
        json.dump({
            "record_id": record_id,
            "session_id": sid,
            "final_status": final_status,
            "race_proven": race_proven,
            "events": [{"ts": ts, "rel_ms": (ts-t0)*1000, "token": tok, "line": ln}
                        for ts, tok, ln in events],
            "poll_history": poll_hist,
            "key_gaps_ms": {
                "tx_commit_to_finalize_start": g1,
                "tx_commit_to_barrier_read": g2,
                "tx_commit_to_snapshot_read": g3,
                "enqueue_to_finalize_start":
                    (ts_fin_start - ts_enqueue)*1000 if ts_fin_start and ts_enqueue else None,
            }
        }, f, indent=2, default=str)
    log.info(f"Trace: {out_path}")


if __name__ == "__main__":
    main()
