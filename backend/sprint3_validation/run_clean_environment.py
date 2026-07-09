import os, sys, django
sys.path.insert(0,".")
os.environ.setdefault("DJANGO_SETTINGS_MODULE","backend.settings")
django.setup()

import redis
from core.sqs import queue_service

def clean_env():
    print("=== Phase 1: Environment Clean ===")
    
    # 1. Flush Redis
    try:
        redis_url = f"redis://{os.getenv('REDIS_HOST', 'localhost')}:{os.getenv('REDIS_PORT', '6379')}/0"
        r = redis.Redis.from_url(redis_url)
        r.flushdb()
        print("[CLEAN] Redis database flushed.")
    except Exception as e:
        print(f"[CLEAN] Redis flush failed: {e}")
        
    # 2. Drain SQS Queues
    roles = ['ingestion', 'ai', 'assembly', 'finalize', 'export', 'materialization']
    for role in roles:
        try:
            print(f"[CLEAN] Draining SQS queue role={role}...")
            popped = 0
            while True:
                # Poll with short wait time
                msgs = queue_service.receive(role, max_messages=10, wait_time=1, suppress_empty_log=True)
                if not msgs:
                    break
                for m in msgs:
                    queue_service.delete(m['_sqs_handle'], role)
                    popped += 1
            print(f"[CLEAN] SQS queue role={role} drained. Popped count: {popped}")
        except Exception as e:
            print(f"[CLEAN] SQS queue role={role} drain failed: {e}")

if __name__ == '__main__':
    clean_env()
