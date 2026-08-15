"""
Django Management Command: index_knowledge
===========================================
Executes Developer-Managed Global Knowledge Base Indexing into ChromaDB.
Hardened for Phase 19: Eagerly preloads local BGE CUDA model and fails loudly
if embedding fails or if corpus becomes OUT_OF_SYNC.
"""
from django.core.management.base import BaseCommand
from core.kiki.rag.knowledge_indexer import knowledge_indexer
from core.kiki.rag.providers.embedding_provider import bge_embedding_provider


class Command(BaseCommand):
    help = "Indexes developer-managed global knowledge documents into ChromaDB collection 'finpixe_global_knowledge'."

    def add_arguments(self, parser):
        parser.add_argument(
            '--rebuild',
            action='store_true',
            help='Deletes existing global ChromaDB collection and rebuilds from scratch.',
        )

    def handle(self, *args, **options):
        rebuild = options.get('rebuild', False)
        self.stdout.write(self.style.NOTICE("=== KIKI GLOBAL KNOWLEDGE INDEXER ==="))
        self.stdout.write(f"Scanning knowledge repository: {knowledge_indexer.knowledge_dir}\n")

        # 1. Eager Preload BGE Model on CUDA
        self.stdout.write("Eagerly preloading BGE CUDA embedding provider...")
        try:
            bge_embedding_provider.preload()
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"[ERROR] Preload failed: {e}"))
            raise RuntimeError(f"INDEXING_ABORTED_PRELOAD_FAILED: {e}") from e

        report = knowledge_indexer.index_all(rebuild=rebuild)

        sync_status = report.get("corpus_sync_status", "UNKNOWN")
        total_chunks = report.get("total_chunks", 0)
        failed_files = [f for f in report.get("file_details", []) if "FAILED" in f.get("status", "")]

        if total_chunks == 0 or sync_status != "SYNCHRONIZED" or failed_files:
            self.stderr.write(self.style.ERROR(f"\n--- INDEXING FAILURE REPORT ---"))
            self.stderr.write(f"Global Collection Name : {report.get('collection')}")
            self.stderr.write(f"Total Documents Scanned: {report.get('total_documents')}")
            self.stderr.write(f"Total Chunks Indexed   : {total_chunks}")
            self.stderr.write(f"Corpus Sync Status     : {sync_status}")
            self.stderr.write(f"Failed Files Count     : {len(failed_files)}")
            
            for item in failed_files:
                self.stderr.write(self.style.ERROR(f"  FAILED: {item['filename']} -> {item['status']}"))

            self.stderr.write(self.style.ERROR("\n[FAILED] Global Knowledge Indexing Failed or Out of Sync!\n"))
            raise RuntimeError(f"INDEXING_FAILED: total_chunks={total_chunks}, sync_status={sync_status}")

        self.stdout.write(self.style.SUCCESS(f"\n--- INDEXING SUMMARY REPORT ---"))
        self.stdout.write(f"Global Collection Name : {report['collection']}")
        self.stdout.write(f"Total Documents Scanned: {report['total_documents']}")
        self.stdout.write(f"Total Pages Parsed     : {report['total_pages']}")
        self.stdout.write(f"Total Chunks Indexed   : {report['total_chunks']}")
        self.stdout.write(f"Corpus Sync Status     : {self.style.SUCCESS(sync_status)}")
        self.stdout.write(f"Execution Latency      : {report['execution_time_seconds']}s\n")

        self.stdout.write(self.style.MIGRATE_HEADING("DETAILS BY FILE:"))
        for item in report.get("file_details", []):
            status_color = self.style.SUCCESS if item['status'] == 'SUCCESS' else self.style.ERROR
            self.stdout.write(
                f"  [{item['category']}] {item['filename']} -> Pages: {item['pages']} | Chunks: {item['chunks']} | Status: {status_color(item['status'])}"
            )

        self.stdout.write(self.style.SUCCESS("\n[SUCCESS] Global Knowledge Indexing Complete & Synchronized!\n"))
