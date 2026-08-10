"""
KIKI Management Command: rag_status — Phase 17.4 Expanded
==========================================================
Full RAG subsystem health dashboard. Displays embedding model, reranker, Chroma provenance,
BM25 provenance, corpus sync status, active index pointer, and recent reindex job history.
"""
from django.core.management.base import BaseCommand  # type: ignore
from core.kiki.rag.runtime_manager import rag_runtime_manager
from core.kiki.rag.providers.embedding_provider import bge_embedding_provider
from core.kiki.rag.providers.reranker_provider import local_reranker_provider
from core.kiki.rag.providers.chroma_provider import chroma_vector_store_provider
from core.kiki.rag.pipeline.sparse_engine import bm25_sparse_engine
from core.kiki.rag.corpus_sync import validate_rag_corpus_sync
from core.kiki.config import kiki_settings
from core.models import RAGActiveIndex, RAGReindexJob


class Command(BaseCommand):
    help = "Full KIKI RAG subsystem health dashboard (Phase 17.4)."

    def add_arguments(self, parser):
        parser.add_argument(
            '--init',
            action='store_true',
            help='Run RAG runtime initialization and model preloading before reporting status.',
        )

    def handle(self, *args, **options):
        SEP = "=" * 60
        sep = "-" * 60

        if options.get('init'):
            self.stdout.write("Running RAG runtime initialization...")
            rag_runtime_manager.initialize()

        self.stdout.write(self.style.SUCCESS(f"\n{SEP}"))
        self.stdout.write(self.style.SUCCESS("  KIKI RAG SUBSYSTEM STATUS — Phase 17.4"))
        self.stdout.write(self.style.SUCCESS(f"{SEP}\n"))

        # ── 1. Runtime State ──────────────────────────────────────────────────
        status_info = rag_runtime_manager.status()
        rag_state = status_info["status"]

        state_color = self.style.SUCCESS if rag_state in ("READY",) else (
            self.style.WARNING if rag_state in ("DEGRADED", "MIGRATION_REQUIRED") else
            self.style.ERROR
        )
        self.stdout.write(f"RAG State       : {state_color(rag_state)}")
        self.stdout.write(f"Last Error      : {status_info.get('last_error') or 'None'}")

        # ── 2. Embedding Provider ─────────────────────────────────────────────
        self.stdout.write(f"\n{sep}")
        self.stdout.write("EMBEDDING PROVIDER")
        self.stdout.write(sep)
        embed = status_info.get("embedding_provider", {})
        loaded_str = self.style.SUCCESS("✅ LOADED") if embed.get("is_loaded") else self.style.ERROR("❌ NOT LOADED")
        self.stdout.write(f"Model ID        : {embed.get('model_id') or 'NOT CONFIGURED'}")
        self.stdout.write(f"Dimension       : {embed.get('dimension') or 0}")
        self.stdout.write(f"Distance Metric : {embed.get('distance_metric') or 'N/A'}")
        self.stdout.write(f"Normalized      : {embed.get('normalized')}")
        self.stdout.write(f"Status          : {loaded_str}")

        # ── 3. Reranker ───────────────────────────────────────────────────────
        self.stdout.write(f"\n{sep}")
        self.stdout.write("RERANKER PROVIDER")
        self.stdout.write(sep)
        reranker = status_info.get("reranker_provider", {})
        rer_loaded = self.style.SUCCESS("✅ LOADED") if reranker.get("is_loaded") else self.style.WARNING("⚠️  NOT LOADED (Degraded)")
        self.stdout.write(f"Model           : {reranker.get('model') or kiki_settings.RERANKER_MODEL}")
        self.stdout.write(f"Status          : {rer_loaded}")

        # ── 4. Chroma Provenance ──────────────────────────────────────────────
        self.stdout.write(f"\n{sep}")
        self.stdout.write("CHROMA VECTOR STORE (PRIMARY)")
        self.stdout.write(sep)
        vprov = status_info.get("vector_provenance", {})
        chroma_chunks = vprov.get("chunk_count", chroma_vector_store_provider.count())
        self.stdout.write(f"Collection      : {kiki_settings.PRIMARY_COLLECTION_NAME}")
        self.stdout.write(f"Chunk Count     : {chroma_chunks}")
        self.stdout.write(f"Embedding Model : {vprov.get('embedding_model') or '⚠️  MISSING'}")
        self.stdout.write(f"Dimension       : {vprov.get('embedding_dimension') or '⚠️  MISSING'}")
        self.stdout.write(f"Corpus Version  : {vprov.get('corpus_version') or 'N/A'}")
        self.stdout.write(f"Index Version   : {vprov.get('index_version') or 'N/A'}")
        self.stdout.write(f"Created At      : {vprov.get('created_at') or 'N/A'}")
        is_compatible, reason = chroma_vector_store_provider.validate_provenance()
        prov_color = self.style.SUCCESS if is_compatible else self.style.ERROR
        self.stdout.write(f"Provenance      : {prov_color(reason)}")

        # ── 5. BM25 Provenance ────────────────────────────────────────────────
        self.stdout.write(f"\n{sep}")
        self.stdout.write("BM25 SPARSE INDEX")
        self.stdout.write(sep)
        bm25_prov = status_info.get("bm25_provenance", bm25_sparse_engine.get_provenance())
        self.stdout.write(f"Chunk Count     : {bm25_sparse_engine.count()}")
        self.stdout.write(f"Corpus Version  : {bm25_prov.get('corpus_version') or '⚠️  LEGACY (no provenance)'}")
        self.stdout.write(f"Index Version   : {bm25_prov.get('index_version') or 'LEGACY'}")
        self.stdout.write(f"Created At      : {bm25_prov.get('created_at') or 'UNKNOWN'}")
        self.stdout.write(f"Manifest Size   : {bm25_prov.get('corpus_manifest_size', 0)} chunks tracked")

        # ── 6. Corpus Sync ────────────────────────────────────────────────────
        self.stdout.write(f"\n{sep}")
        self.stdout.write("CORPUS SYNCHRONIZATION")
        self.stdout.write(sep)
        try:
            sync = validate_rag_corpus_sync()
            sync_status = sync.get("sync_status", "UNKNOWN")
            sync_color = self.style.SUCCESS if sync_status == "SYNCHRONIZED" else self.style.ERROR
            self.stdout.write(f"Sync Status     : {sync_color(sync_status)}")
            self.stdout.write(f"Dense Count     : {sync.get('dense_chunk_count')}")
            self.stdout.write(f"Sparse Count    : {sync.get('sparse_chunk_count')}")
            self.stdout.write(f"Common          : {sync.get('common_chunk_count')}")
            self.stdout.write(f"Missing/Dense   : {sync.get('missing_from_dense')}")
            self.stdout.write(f"Missing/Sparse  : {sync.get('missing_from_sparse')}")
            if sync_status != "SYNCHRONIZED":
                self.stdout.write(self.style.WARNING(
                    "\n  ⚠️  Run: python manage.py index_knowledge --rebuild to fix corpus divergence"
                ))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Sync check failed: {e}"))

        # ── 7. Active Index Pointer ───────────────────────────────────────────
        self.stdout.write(f"\n{sep}")
        self.stdout.write("ACTIVE INDEX POINTER (DATABASE)")
        self.stdout.write(sep)
        active_ptr = RAGActiveIndex.objects.order_by('-promoted_at').first()
        if active_ptr:
            self.stdout.write(f"Active Version  : {active_ptr.active_index_version}")
            self.stdout.write(f"Model           : {active_ptr.embedding_model} ({active_ptr.embedding_dimension}-dim)")
            self.stdout.write(f"Promoted At     : {active_ptr.promoted_at}")
        else:
            self.stdout.write("No active index promoted yet.")

        # ── 8. NLU State ──────────────────────────────────────────────────────
        self.stdout.write(f"\n{sep}")
        self.stdout.write("NLU CONFIGURATION")
        self.stdout.write(sep)
        self.stdout.write(f"NLU Bypass      : {'ENABLED' if kiki_settings.NLU_BYPASS_ENABLED else 'DISABLED'}")
        self.stdout.write(f"Anon Tenant     : {'ALLOWED' if kiki_settings.TENANT_ANONYMOUS_ALLOWED else 'BLOCKED (fail-closed)'}")

        # ── 9. Recent Reindex Jobs ────────────────────────────────────────────
        self.stdout.write(f"\n{sep}")
        self.stdout.write("RECENT REINDEX JOBS (last 5)")
        self.stdout.write(sep)
        jobs = RAGReindexJob.objects.order_by('-created_at')[:5]
        if jobs:
            for j in jobs:
                j_color = self.style.SUCCESS if j.status == "REINDEX_PROMOTED" else (
                    self.style.ERROR if "FAILED" in j.status else self.style.WARNING
                )
                self.stdout.write(
                    f"  {j_color(j.status):30s} | Target: {j.target_index_version} | {j.created_at}"
                )
        else:
            self.stdout.write("  No reindex jobs found.")

        self.stdout.write(f"\n{SEP}\n")
