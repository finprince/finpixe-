"""
KIKI Management Command: rag_rollback
=====================================
Restores a previous known-good active vector index pointer in DB.
"""
from django.core.management.base import BaseCommand, CommandError  # type: ignore
from django.db import transaction  # type: ignore
from core.models import RAGActiveIndex


class Command(BaseCommand):
    help = "Restores a previous active vector index pointer in DB."

    def add_arguments(self, parser):
        parser.add_argument('index_version', type=str, help='Target collection index version ID to restore.')

    def handle(self, *args, **options):
        version = options['index_version']
        target_index = RAGActiveIndex.objects.filter(active_index_version=version).first()

        if not target_index:
            raise CommandError(f"Index version '{version}' not found in RAGActiveIndex history.")

        with transaction.atomic():
            RAGActiveIndex.objects.create(
                active_index_version=target_index.active_index_version,
                corpus_version=target_index.corpus_version,
                embedding_model=target_index.embedding_model,
                embedding_dimension=target_index.embedding_dimension,
                distance_metric=target_index.distance_metric,
                normalized=target_index.normalized
            )

        self.stdout.write(self.style.SUCCESS(f"Successfully rolled back active vector index to '{version}'."))
