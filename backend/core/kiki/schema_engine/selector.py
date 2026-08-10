"""
Dynamic Schema Selector & Pruner
================================
Prunes 300+ database tables down to only the 3-5 relevant domain tables (~400 tokens) for LLM context optimization.
"""
from typing import Dict, Any, List
from ..metadata import metadata_registry
from ..ontology import ontology_graph

class SchemaSelector:
    """Prunes full database schema down to target business domain tables."""

    def select_schema_for_domain(self, domain_name: str) -> Dict[str, Any]:
        """Select only relevant tables and columns for the given domain."""
        full_catalog = metadata_registry.get_catalog()
        target_tables = ontology_graph.get_tables_for_domain(domain_name)
        
        pruned_schema = {
            "domain": domain_name,
            "tables": {},
            "relationships": []
        }
        
        all_db_tables = full_catalog.get("tables", {})
        
        # If domain target tables exist in DB, include their columns
        for t_name in target_tables:
            if t_name in all_db_tables:
                pruned_schema["tables"][t_name] = all_db_tables[t_name]

        # If no explicit domain tables match, select top 5 database tables as fallback
        if not pruned_schema["tables"]:
            for t_name, t_info in list(all_db_tables.items())[:5]:
                pruned_schema["tables"][t_name] = t_info

        # Filter relevant foreign keys
        for fk in full_catalog.get("foreign_keys", []):
            if fk["from_table"] in pruned_schema["tables"] and fk["to_table"] in pruned_schema["tables"]:
                pruned_schema["relationships"].append(fk)

        return pruned_schema

schema_selector = SchemaSelector()
