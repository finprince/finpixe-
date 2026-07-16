"""
PHASE 2-8: Backend Log Monitor - watches debug.log for new entries after baseline.
Run this AFTER uploading the invoice and clicking Finalize.
Captures all relevant entries: timing, errors, GST, voucher, lock events.
"""
import time
import re
import subprocess

LOG_FILE = r"c:\108\AI-accounting-0.03\backend\logs\debug.log"
BASELINE_LINES = 538951  # Line count at start of investigation

# Key patterns to watch
PATTERNS = {
    'FINALIZE': re.compile(r'FINALIZE|finalize', re.IGNORECASE),
    'VOUCHER': re.compile(r'VOUCHER|voucher', re.IGNORECASE),
    'GST': re.compile(r'GST|gst_mismatch|GST_MISMATCH|gst_audit', re.IGNORECASE),
    'ERROR': re.compile(r'ERROR|error|CRITICAL|critical', re.IGNORECASE),
    'LOCK': re.compile(r'LOCK|lock|DISTRIBUTED_LOCK', re.IGNORECASE),
    'TIMING': re.compile(r'ms|duration|elapsed|time'),
    'ATOMIC': re.compile(r'atomic|transaction|ROLLBACK|COMMIT', re.IGNORECASE),
    'SAVE': re.compile(r'SAVE|save|insert|INSERT', re.IGNORECASE),
    'ELIGIBLE': re.compile(r'eligible|ELIGIBLE|ready_count|READY_COUNT'),
    'BLOCK': re.compile(r'BLOCK|block|BLOCKED|blocked', re.IGNORECASE),
    'SESSION': re.compile(r'FINALIZE_START|SAVE_PIPELINE|SESSION_ROW_SCOPE'),
    'UPLOAD': re.compile(r'UPLOAD|upload|ocr_staging|OCR_STAGING', re.IGNORECASE),
}

print(f"[MONITOR] Watching {LOG_FILE} from line {BASELINE_LINES}")
print(f"[MONITOR] Waiting for new log entries...")
print("="*80)

def read_new_lines():
    with open(LOG_FILE, 'r', encoding='utf-8', errors='replace') as f:
        lines = f.readlines()
    return lines[BASELINE_LINES:]

last_count = 0
capture_all = False  # Set to True when FINALIZE_START is seen

while True:
    try:
        new_lines = read_new_lines()
        if len(new_lines) > last_count:
            for line in new_lines[last_count:]:
                line = line.strip()
                if not line:
                    continue
                    
                # Always print FINALIZE-related
                if any(p.search(line) for p in [PATTERNS['FINALIZE'], PATTERNS['SESSION']]):
                    print(f"[FINALIZE] {line}")
                    if 'FINALIZE_START' in line:
                        capture_all = True
                        
                # Print errors always
                elif any(x in line for x in ['ERROR', 'CRITICAL', 'ROLLBACK', 'EXCEPTION', 'Traceback']):
                    print(f"[!!!] {line}")
                    
                # Print GST related
                elif PATTERNS['GST'].search(line):
                    print(f"[GST] {line}")
                    
                # Print lock events
                elif PATTERNS['LOCK'].search(line):
                    print(f"[LOCK] {line}")
                    
                # Print save eligible
                elif PATTERNS['ELIGIBLE'].search(line):
                    print(f"[ELIG] {line}")
                    
                # Print voucher events
                elif any(x in line for x in ['VOUCHER_INSERT', 'PURCHASE_DB_INSERT', 'SAVE_PIPELINE', 'ATOMIC_SAVE']):
                    print(f"[SAVE] {line}")
                    
                # If in finalize context, print everything
                elif capture_all:
                    print(f"[LOG] {line}")
                    
            last_count = len(new_lines)
    except Exception as e:
        print(f"[ERROR] {e}")
    
    time.sleep(1)
