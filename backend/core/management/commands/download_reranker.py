"""
KIKI Management Command: download_reranker — Phase 17.4 New
=============================================================
Pre-downloads cross-encoder reranker model weights during deployment/setup.
Guarantees zero model download latency during HTTP user requests.
"""
from django.core.management.base import BaseCommand  # type: ignore
from core.kiki.config import kiki_settings
from core.kiki.rag.providers.reranker_provider import local_reranker_provider


class Command(BaseCommand):
    help = "Pre-download cross-encoder reranker model weights for offline deployment."

    def handle(self, *args, **options):
        model_name = getattr(kiki_settings, "RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
        self.stdout.write(f"Preloading reranker model '{model_name}'...")

        success = local_reranker_provider.preload()

        if success and local_reranker_provider.is_loaded():
            self.stdout.write(self.style.SUCCESS(
                f"✅ Cross-encoder reranker '{model_name}' downloaded and loaded successfully!"
            ))
        else:
            self.stdout.write(self.style.WARNING(
                f"⚠️  Reranker preloading completed in degraded mode. System will pass through RRF candidates."
            ))
