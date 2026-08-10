"""
KIKI Management Command: rag_promote
====================================
Atomically promotes a validated candidate index to active in DB.
"""
from django.core.management.base import BaseCommand, CommandError  # type: ignore
from django.db import transaction  # type: ignore
from core.models import RAGActiveIndex, RAGReindexJob
from core.kiki.rag.providers.embedding_provider import bge_embedding_provider


class Command(BaseCommand):
    help = "Atomically promotes a candidate vector index to active in DB."

    def add_arguments(self, parser):
        parser.add_argument('index_version', type=str, help='Target collection index version ID to promote.')

    def handle(self, *args, **options):
        version = options['index_version']
        caps = bge_embedding_provider.capabilities()

        with transaction.atomic():
            active_ptr = RAGActiveIndex.objects.create(
                active_index_version=version,
                corpus_version="corpus_promoted",
                embedding_model=caps.model_id,
                embedding_dimension=caps.dimension,
                distance_metric=caps.distance_metric,
                normalized=caps.normalized
            )

        self.stdout.write(self.style.SUCCESS(f"Atomically promoted index '{version}' to active. Promoted At: {active_ptr.promoted_at}"))
