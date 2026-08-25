import os
import sys
import psutil
import json
import redis
import boto3

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from dotenv import load_dotenv
load_dotenv(os.path.join(project_root, '.env'))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
import django
django.setup()

from django.db import connections
from core.sqs import queue_service
from core.ai_proxy import validate_ai_on_startup

report = {}

# 1. Workers
worker_map = {}
for p in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        cmdline = p.info.get('cmdline')
        if not cmdline: continue
        cmd_str = ' '.join(cmdline)
        if 'worker_watchdog.py' in cmd_str:
            role = cmdline[-1]
            worker_map[f"watchdog_{role}"] = p.info['pid']
        elif 'unified_worker.py' in cmd_str:
            for idx, arg in enumerate(cmdline):
                if arg == '--role' and idx + 1 < len(cmdline):
                    worker_map[f"worker_{cmdline[idx+1]}"] = p.info['pid']
        elif 'start_cluster.py' in cmd_str:
            worker_map['cluster_bootstrap'] = p.info['pid']
        elif 'manage.py runserver' in cmd_str:
            worker_map.setdefault('api_server', []).append(p.info['pid'])
    except Exception:
        pass

report['workers'] = worker_map

# 2. SQS
sqs_info = {}
for role in ['ingestion', 'ai', 'assembly', 'finalize', 'export', 'materialization']:
    url = queue_service._get_queue_url(role)
    depth = queue_service.get_queue_depth(role)
    sqs_info[role] = {'url': url, 'depth': depth}
report['sqs'] = sqs_info

# 3. Redis
r = redis.Redis(host=os.getenv('REDIS_HOST', 'localhost'), port=int(os.getenv('REDIS_PORT', 6379)), db=0)
report['redis'] = {
    'connected': r.ping(),
    'host': os.getenv('REDIS_HOST', 'localhost'),
    'port': os.getenv('REDIS_PORT', 6379),
    'db': 0,
    'total_keys': len(r.keys('*'))
}

# 4. Database
conn = connections['default']
conn.ensure_connection()
report['database'] = {
    'connected': conn.is_usable(),
    'vendor': conn.vendor,
    'db_name': conn.settings_dict.get('NAME'),
    'user': conn.settings_dict.get('USER'),
    'host': conn.settings_dict.get('HOST', 'localhost'),
    'port': conn.settings_dict.get('PORT', 3306)
}

# 5. AI / Model
ai_ready = validate_ai_on_startup()
report['ai_provider'] = {
    'provider': 'Mistral Cloud API',
    'model': os.getenv('MISTRAL_OCR_MODEL', 'mistral-ocr-latest'),
    'ready': ai_ready,
    'api_key_set': bool(os.getenv('MISTRAL_API_KEY')),
    'max_retries': int(os.getenv('MISTRAL_OCR_MAX_RETRIES', 3)),
    'retry_delay_s': float(os.getenv('MISTRAL_OCR_RETRY_DELAY_S', 2.0))
}

# 6. Concurrency & Compute
import torch
gpu_available = False
gpu_device_name = "N/A"
try:
    import torch
    gpu_available = torch.cuda.is_available()
    if gpu_available:
        gpu_device_name = torch.cuda.get_device_name(0)
except Exception:
    pass

report['compute_and_concurrency'] = {
    'cpu_count': os.cpu_count(),
    'gpu_available': gpu_available,
    'gpu_name': gpu_device_name,
    'ai_global_concurrency': int(os.getenv('AI_GLOBAL_CONCURRENCY', 10)),
    'worker_concurrency': int(os.getenv('WORKER_CONCURRENCY', 4)),
    'ai_max_rps': int(os.getenv('AI_MAX_RPS', 5)),
    'max_pages_per_job': int(os.getenv('MAX_PAGES_PER_JOB', 50)),
    'ocr_dpi': int(os.getenv('OCR_DEFAULT_DPI', 350))
}

print(json.dumps(report, indent=2))
