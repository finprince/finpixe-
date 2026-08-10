"""
KIKI Management Command: reindex_kiki_knowledge
================================================
Triggers or executes background knowledge reindexing operations.
Supports --full, --incremental, and --async options.
"""
from django.core.management.base import BaseCommand  # type: ignore
from core.kiki.rag.reindex_manager import reindex_job_manager


class Command(BaseCommand):
    help = "Triggers knowledge reindexing pipeline out-of-band."

    def add_arguments(self, parser):
        parser.add_argument('--full', action='store_true', help='Force a full reindex of the knowledge base.')
        parser.add_argument('--incremental', action='store_true', help='Run incremental reindex for changed documents.')
        parser.add_argument('--async', action='store_true', help='Schedule job asynchronously via Celery task.')

    def handle(self, *args, **options):
        trigger_type = "MANUAL_COMMAND"
        reason = "Manual admin invocation"
        if options.get('full'):
            reason = "Manual admin full reindex invocation"

        job = reindex_job_manager.create_reindex_job(trigger_type=trigger_type, reason=reason)
        self.stdout.write(self.style.SUCCESS(f"Created reindex job '{job.job_id}' for target collection '{job.target_index_version}'."))

        if options.get('async'):
            try:
                from core.kiki.rag.tasks import run_async_reindex_job
                run_async_reindex_job.delay(job.job_id)
                self.stdout.write(self.style.SUCCESS(f"Scheduled job '{job.job_id}' asynchronously via Celery."))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Celery dispatch fallback to direct execution: {str(e)}"))
                success = reindex_job_manager.execute_reindex_job(job.job_id)
                status_str = "SUCCESS" if success else "FAILED"
                self.stdout.write(self.style.SUCCESS(f"Job execution completed: {status_str}"))
        else:
            self.stdout.write("Executing reindex job synchronously...")
            success = reindex_job_manager.execute_reindex_job(job.job_id)
            status_str = "SUCCESS" if success else "FAILED"
            self.stdout.write(self.style.SUCCESS(f"Job execution completed: {status_str}"))
