import psutil
import os
import sys

print("=== RUNNING RELEVANT PROCESSES ===")
current_pid = os.getpid()
for p in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        cmdline = p.info.get('cmdline')
        if not cmdline:
            continue
        cmd_str = ' '.join(cmdline)
        if any(term in cmd_str.lower() for term in ['python', 'manage.py', 'start_cluster', 'unified_worker', 'worker_watchdog', 'uvicorn', 'gunicorn']):
            print(f"PID: {p.info['pid']} | Name: {p.info['name']} | CMD: {cmd_str}")
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass
