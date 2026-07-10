import os
import shutil
import django
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CleanRuntime")

# Set up Django environment
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from core.sqs import QueueService

def purge_sqs_queues():
    logger.info("Starting SQS queue purging...")
    qs = QueueService()
    sqs_client = qs._get_sqs_client()
    if not sqs_client:
        logger.error("SQS client could not be initialized.")
        return

    roles = ['ingestion', 'ai', 'assembly', 'finalize', 'export', 'materialization']
    for role in roles:
        url = qs._get_queue_url(role)
        if not url:
            logger.warning(f"No SQS URL found for role: {role}")
            continue
        
        logger.info(f"Purging queue for role '{role}' (URL: {url})...")
        try:
            sqs_client.purge_queue(QueueUrl=url)
            logger.info(f"Successfully purged queue: {role}")
        except Exception as e:
            logger.warning(f"Could not purge queue {role} using purge_queue ({e}). Falling back to manual receive & delete...")
            # Fallback manual empty
            try:
                purged_count = 0
                while True:
                    res = sqs_client.receive_message(
                        QueueUrl=url,
                        MaxNumberOfMessages=10,
                        WaitTimeSeconds=1,
                        VisibilityTimeout=10
                    )
                    messages = res.get('Messages', [])
                    if not messages:
                        break
                    for msg in messages:
                        sqs_client.delete_message(QueueUrl=url, ReceiptHandle=msg['ReceiptHandle'])
                        purged_count += 1
                logger.info(f"Manually purged {purged_count} messages from queue: {role}")
            except Exception as ex:
                logger.error(f"Failed to manually purge queue {role}: {ex}")

def clear_temp_folders():
    logger.info("Clearing temporary folders...")
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    media_root = os.path.join(base_dir, 'media', 'bulk_pipeline')
    
    ocr_dir = os.path.join(media_root, 'ocr')
    snapshot_dir = os.path.join(media_root, 'snapshots')

    for d in [ocr_dir, snapshot_dir]:
        if os.path.exists(d):
            logger.info(f"Scanning directory for removal: {d}")
            for item in os.listdir(d):
                item_path = os.path.join(d, item)
                try:
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                        logger.info(f"Deleted directory: {item_path}")
                    else:
                        os.remove(item_path)
                        logger.info(f"Deleted file: {item_path}")
                except Exception as e:
                    logger.error(f"Error removing {item_path}: {e}")
        else:
            logger.warning(f"Directory does not exist: {d}")

if __name__ == '__main__':
    purge_sqs_queues()
    clear_temp_folders()
    logger.info("Clean-room runtime clean complete.")
