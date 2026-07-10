import os
import sys
import time
import django
import logging
import platform
import psutil

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("InfraHealthCheck")

# Add backend directory to python path
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

# Initialize Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

def check_redis():
    logger.info("Checking Redis reachability...")
    try:
        import redis
        host = os.getenv('REDIS_HOST', 'localhost')
        port = int(os.getenv('REDIS_PORT', 6379))
        r = redis.Redis(host=host, port=port, db=0)
        pong = r.ping()
        dbsize = r.dbsize()
        logger.info(f"  Redis is UP. Host: {host}:{port}, Ping: {pong}, Keys: {dbsize}")
        return True, f"UP (Keys: {dbsize})"
    except Exception as e:
        logger.error(f"  Redis check failed: {e}")
        return False, str(e)

def check_mysql():
    logger.info("Checking MySQL reachability...")
    try:
        from django.db import connections
        connections['default'].ensure_connection()
        with connections['default'].cursor() as cursor:
            cursor.execute("SELECT VERSION();")
            ver = cursor.fetchone()[0]
        logger.info(f"  MySQL is UP. Version: {ver}")
        return True, f"UP (Version: {ver})"
    except Exception as e:
        logger.error(f"  MySQL check failed: {e}")
        return False, str(e)

def check_sqs():
    logger.info("Checking SQS reachability...")
    try:
        from core.sqs import queue_service
        roles = ['ingestion', 'ai', 'assembly', 'finalize', 'export', 'materialization']
        stats = {}
        all_ok = True
        for role in roles:
            url = queue_service._get_queue_url(role)
            depth = queue_service.get_queue_depth(role)
            stats[role] = {"url": url, "depth": depth}
            logger.info(f"  SQS Queue '{role}': depth={depth}, URL={url}")
        return True, stats
    except Exception as e:
        logger.error(f"  SQS check failed: {e}")
        return False, str(e)

def check_s3():
    logger.info("Checking S3 reachability...")
    try:
        from core.storage import StorageService
        storage = StorageService()
        if not storage.bucket:
            logger.warning("  S3 bucket name not set. Running in local fallback mode.")
            return True, "LOCAL FALLBACK MODE"
        
        # Test put/get object
        test_key = "health_check_test.txt"
        test_bytes = b"health check"
        storage.upload_file(test_bytes, test_key, content_type='text/plain')
        retrieved = storage.get_file(test_key)
        
        # Cleanup
        if storage.s3:
            storage.s3.delete_object(Bucket=storage.bucket, Key=test_key)
            
        if retrieved == test_bytes:
            logger.info(f"  S3 is UP. Bucket: {storage.bucket}")
            return True, f"UP (Bucket: {storage.bucket})"
        else:
            raise ValueError("Retrieved bytes do not match uploaded bytes.")
    except Exception as e:
        logger.error(f"  S3 check failed: {e}")
        return False, str(e)

def check_mistral_api():
    logger.info("Checking Mistral API reachability...")
    try:
        from core.ai_proxy import validate_ai_on_startup
        ok = validate_ai_on_startup()
        if ok:
            logger.info("  Mistral API is UP and key is healthy.")
            return True, "UP & HEALTHY"
        else:
            logger.error("  Mistral API startup check failed.")
            return False, "HEALTHCHECK FAILED"
    except Exception as e:
        logger.error(f"  Mistral API check failed: {e}")
        return False, str(e)

def check_internet():
    logger.info("Checking Internet connectivity...")
    try:
        import urllib.request
        # Ping google.com via HTTP request
        urllib.request.urlopen("https://www.google.com", timeout=5)
        logger.info("  Internet connectivity is UP.")
        return True, "UP"
    except Exception as e:
        logger.error(f"  Internet connectivity check failed: {e}")
        return False, str(e)

def check_system_resources():
    logger.info("Checking System Resources...")
    try:
        # Disk Space
        disk = psutil.disk_usage('/')
        disk_free_gb = disk.free / (1024 ** 3)
        disk_total_gb = disk.total / (1024 ** 3)
        
        # RAM
        mem = psutil.virtual_memory()
        mem_free_gb = mem.available / (1024 ** 3)
        mem_total_gb = mem.total / (1024 ** 3)
        
        # CPU
        cpu_percent = psutil.cpu_percent(interval=0.5)
        
        logger.info(f"  CPU: {cpu_percent}%, RAM: {mem_free_gb:.2f} GB Free / {mem_total_gb:.2f} GB Total, Disk: {disk_free_gb:.2f} GB Free / {disk_total_gb:.2f} GB Total")
        
        return True, {
            "cpu_percent": cpu_percent,
            "ram_free_gb": round(mem_free_gb, 2),
            "ram_total_gb": round(mem_total_gb, 2),
            "disk_free_gb": round(disk_free_gb, 2),
            "disk_total_gb": round(disk_total_gb, 2)
        }
    except Exception as e:
        logger.error(f"  System resources check failed: {e}")
        return False, str(e)

def run_health_check():
    print("\n" + "="*50)
    print("INFRASTRUCTURE HEALTH CHECK")
    print("="*50 + "\n")
    
    results = {}
    
    internet_ok, internet_res = check_internet()
    results['internet'] = (internet_ok, internet_res)
    
    redis_ok, redis_res = check_redis()
    results['redis'] = (redis_ok, redis_res)
    
    mysql_ok, mysql_res = check_mysql()
    results['mysql'] = (mysql_ok, mysql_res)
    
    sqs_ok, sqs_res = check_sqs()
    results['sqs'] = (sqs_ok, sqs_res)
    
    s3_ok, s3_res = check_s3()
    results['s3'] = (s3_ok, s3_res)
    
    mistral_ok, mistral_res = check_mistral_api()
    results['mistral'] = (mistral_ok, mistral_res)
    
    sys_ok, sys_res = check_system_resources()
    results['system'] = (sys_ok, sys_res)
    
    # Check overall health
    overall_ok = all([internet_ok, redis_ok, mysql_ok, sqs_ok, s3_ok, mistral_ok, sys_ok])
    
    print("\n" + "="*50)
    print(f"HEALTH CHECK STATUS: {'PASS' if overall_ok else 'FAIL'}")
    print("="*50)
    
    for key, (ok, val) in results.items():
        status = "HEALTHY" if ok else "UNHEALTHY"
        print(f"  {key.upper():<10} : {status:<10} | {val}")
    
    print("="*50 + "\n")
    return overall_ok

if __name__ == '__main__':
    ok = run_health_check()
    sys.exit(0 if ok else 1)
