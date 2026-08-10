"""
Metadata Registry Manager
=========================
Stores and manages active schema topology in memory with lazy boot scanning.
"""
from typing import Dict, Any, Optional
from .scanner import MySQLSchemaScanner
from ..logging import get_kiki_logger

logger = get_kiki_logger("metadata_registry")

class MetadataRegistry:
    _instance: Optional['MetadataRegistry'] = None
    _catalog: Optional[Dict[str, Any]] = None

    def __init__(self):
        self.scanner = MySQLSchemaScanner()

    @classmethod
    def get_instance(cls) -> 'MetadataRegistry':
        if cls._instance is None:
            cls._instance = MetadataRegistry()
        return cls._instance

    def get_catalog(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Return the current database schema catalog."""
        if self._catalog is None or force_refresh:
            logger.info("Scanning MySQL DB topology for Metadata Catalog...")
            self._catalog = self.scanner.scan_schema()
            table_count = len(self._catalog.get("tables", {}))
            fk_count = len(self._catalog.get("foreign_keys", []))
            logger.info(f"Metadata Catalog refreshed: {table_count} tables, {fk_count} foreign key relationships discovered.")
        return self._catalog

    def get_columns(self, table_name: str) -> list:
        """Return list of column dict objects for a table."""
        catalog = self.get_catalog()
        cols_dict = catalog.get("tables", {}).get(table_name, {}).get("columns", {})
        return [{"name": k, **v} if isinstance(v, dict) else {"name": k} for k, v in cols_dict.items()]

metadata_registry = MetadataRegistry.get_instance()
