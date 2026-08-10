"""
Django Management Command: index_knowledge
===========================================
Executes Developer-Managed Global Knowledge Base Indexing into ChromaDB.
"""
from django.core.management.base import BaseCommand
from core.kiki.rag.knowledge_indexer import knowledge_indexer

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

        report = knowledge_indexer.index_all(rebuild=rebuild)

        self.stdout.write(self.style.SUCCESS(f"\n--- INDEXING SUMMARY REPORT ---"))
        self.stdout.write(f"Global Collection Name : {report['collection']}")
        self.stdout.write(f"Total Documents Scanned: {report['total_documents']}")
        self.stdout.write(f"Total Pages Parsed     : {report['total_pages']}")
        self.stdout.write(f"Total Chunks Indexed   : {report['total_chunks']}")
        self.stdout.write(f"Execution Latency      : {report['execution_time_seconds']}s\n")

        self.stdout.write(self.style.MIGRATE_HEADING("DETAILS BY FILE:"))
        for item in report.get("file_details", []):
            status_color = self.style.SUCCESS if item['status'] == 'SUCCESS' else self.style.ERROR
            self.stdout.write(
                f"  [{item['category']}] {item['filename']} -> Pages: {item['pages']} | Chunks: {item['chunks']} | Status: {status_color(item['status'])}"
            )

        self.stdout.write(self.style.SUCCESS("\n[SUCCESS] Global Knowledge Indexing Complete!\n"))
