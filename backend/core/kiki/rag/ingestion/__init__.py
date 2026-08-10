"""
KIKI Ingestion Pipeline Subpackage — Phase 17
==============================================
Exports structured ingestion pipeline, cleaner, structure extractor, metadata generator, and chunk validator.
"""
from .cleaner import TextCleaner, text_cleaner
from .structure import StructureExtractor, structure_extractor
from .metadata import MetadataGenerator, metadata_generator
from .validator import ChunkValidator, ChunkValidationError, chunk_validator
from .pipeline import IngestionPipeline, ingestion_pipeline

__all__ = [
    "TextCleaner",
    "text_cleaner",
    "StructureExtractor",
    "structure_extractor",
    "MetadataGenerator",
    "metadata_generator",
    "ChunkValidator",
    "ChunkValidationError",
    "chunk_validator",
    "IngestionPipeline",
    "ingestion_pipeline"
]
