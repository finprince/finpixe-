"""
KIKI Management Command: validate_rag_sync — Phase 17.4 New
============================================================
Runs corpus synchronization validation and prints a detailed report.
Compares BM25 sparse chunk IDs against Chroma primary + global collection chunk IDs.
"""
from django.core.management.base import BaseCommand  # type: ignore
from core.kiki.rag.corpus_sync import validate_rag_corpus_sync


class Command(BaseCommand):
    help = "Validate that Chroma and BM25 indexes represent the same corpus."

    def add_arguments(self, parser):
        parser.add_argument(
            '--no-global',
            action='store_true',
            help='Skip the global knowledge collection (finpixe_global_knowledge).',
        )

    def handle(self, *args, **options):
        SEP = "=" * 60

        self.stdout.write(self.style.SUCCESS(f"\n{SEP}"))
        self.stdout.write(self.style.SUCCESS("  KIKI RAG CORPUS SYNCHRONIZATION REPORT"))
        self.stdout.write(self.style.SUCCESS(f"{SEP}\n"))

        include_global = not options.get("no_global", False)
        self.stdout.write(f"Checking: primary collection + {'global collection' if include_global else '(global skipped)'}\n")

        try:
            result = validate_rag_corpus_sync(include_global=include_global)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Corpus sync check failed: {e}"))
            return

        sync_status = result.get("sync_status", "UNKNOWN")
        if sync_status == "SYNCHRONIZED":
            status_str = self.style.SUCCESS(f"✅  {sync_status}")
        else:
            status_str = self.style.ERROR(f"❌  {sync_status}")

        self.stdout.write(f"Sync Status             : {status_str}")
        self.stdout.write(f"Dense Chunk Count       : {result.get('dense_chunk_count')}")
        self.stdout.write(f"  Primary Collection    : {result.get('primary_collection_count')}")
        self.stdout.write(f"  Global Collection     : {result.get('global_collection_count')}")
        self.stdout.write(f"Sparse (BM25) Count     : {result.get('sparse_chunk_count')}")
        self.stdout.write(f"Common Chunks           : {result.get('common_chunk_count')}")
        self.stdout.write(f"Missing from Dense      : {result.get('missing_from_dense')}")
        self.stdout.write(f"Missing from Sparse     : {result.get('missing_from_sparse')}")
        self.stdout.write(f"BM25 Corpus Version     : {result.get('bm25_corpus_version') or 'LEGACY'}")
        self.stdout.write(f"BM25 Index Version      : {result.get('bm25_index_version') or 'LEGACY'}")
        self.stdout.write(f"BM25 Created At         : {result.get('bm25_created_at') or 'UNKNOWN'}")

        self.stdout.write(f"\n{SEP}")

        if sync_status != "SYNCHRONIZED":
            self.stdout.write(self.style.WARNING(
                "\n⚠️  Corpus is OUT OF SYNC.\n"
                "To rebuild and synchronize:\n"
                "  python manage.py index_knowledge --rebuild\n"
            ))
        else:
            self.stdout.write(self.style.SUCCESS("\n✅  Corpus is fully synchronized.\n"))
