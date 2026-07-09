import os, sys, django, time
sys.path.insert(0,".")
os.environ.setdefault("DJANGO_SETTINGS_MODULE","backend.settings")
django.setup()

import redis
from django.db import connections
from core.sqs import queue_service
from core.ai_proxy import validate_ai_on_startup

def check_infra():
    print("=== Phase 1: Dependency Check ===")
    
    # 1. Redis check
    try:
        redis_url = f"redis://{os.getenv('REDIS_HOST', 'localhost')}:{os.getenv('REDIS_PORT', '6379')}/0"
        r = redis.Redis.from_url(redis_url)
        r.ping()
        print("[INFRA] Redis connectivity: OK")
    except Exception as e:
        print(f"[INFRA] Redis check failed: {e}")
        
    # 2. Database check
    try:
        connections['default'].ensure_connection()
        print("[INFRA] Database connectivity: OK")
    except Exception as e:
        print(f"[INFRA] Database check failed: {e}")
        
    # 3. SQS check
    try:
        roles = ['ingestion', 'ai', 'assembly', 'finalize', 'export', 'materialization']
        for role in roles:
            depth = queue_service.get_queue_depth(role)
            print(f"[INFRA] SQS queue role={role} depth={depth}")
    except Exception as e:
        print(f"[INFRA] SQS check failed: {e}")
        
    # 4. Mistral connectivity
    try:
        res = validate_ai_on_startup()
        print(f"[INFRA] Mistral API connectivity: {'OK' if res else 'FAILED'}")
    except Exception as e:
        print(f"[INFRA] Mistral API check failed: {e}")

if __name__ == '__main__':
    check_infra()
