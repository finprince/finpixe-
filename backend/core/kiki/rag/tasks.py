"""
KIKI Asynchronous Reindex Background Celery Tasks — Phase 17.1 Zero Hardcode Architecture
========================================================================================
Registers out-of-band Celery tasks for knowledge reindexing operations.
Guarantees user HTTP request path NEVER executes model downloading or corpus reindexing.
"""
from celery import shared_task
from .reindex_manager import reindex_job_manager
from core.kiki.logging import get_kiki_logger

logger = get_kiki_logger("rag_tasks")


@shared_task(name="core.kiki.rag.tasks.run_async_reindex_job")
def run_async_reindex_job(job_id: str) -> bool:
    """Out-of-band Celery task executing background reindex pipeline."""
    logger.info(f"[CELERY TASK] Executing asynchronous reindex task for job '{job_id}'...")
    return reindex_job_manager.execute_reindex_job(job_id=job_id)
