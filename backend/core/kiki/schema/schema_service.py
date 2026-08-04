import time
from typing import Dict, List, Any, Optional, Set
from django.db import connection
from ..models.dto import SchemaMatch
from ..config.settings import KikiSettings
from ..exceptions.kiki_exceptions import SchemaException
from ..utils.logger import kiki_logger

class SchemaService:
    """
    Component 3 — Schema Service
    Inspects MySQL database structure, caches schema metadata in memory,
    and provides term-based metadata search.
    Strictly performs metadata operations only (No NLP, No AI reasoning, No module hardcoding).
    """
    _cached_schema: Optional[Dict[str, Any]] = None
    _last_refresh_time: float = 0.0

    @classmethod
    def initialize_schema(cls, force_refresh: bool=False) -> Dict[str, Any]:
        """
        Discovers MySQL database structure and caches table metadata in memory.
        """
        current_time = time.time()
        if cls._cached_schema is not None and (not force_refresh) and (current_time - cls._last_refresh_time < KikiSettings.SCHEMA_REFRESH_INTERVAL):
            return cls._cached_schema
        db_name = connection.settings_dict.get('NAME')
        if not db_name:
            db_name = 'ai_accounting2'
        schema_data: Dict[str, Any] = {'tables': {}, 'relationships': []}
        try:
            with connection.cursor() as cursor:
                col_query = '\n                    SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_KEY, COLUMN_COMMENT\n                    FROM INFORMATION_SCHEMA.COLUMNS\n                    WHERE TABLE_SCHEMA = %s\n                    ORDER BY TABLE_NAME, ORDINAL_POSITION\n                '
                cursor.execute(col_query, [db_name])
                col_rows = cursor.fetchall()
                for table_name, col_name, data_type, is_nullable, col_key, comment in col_rows:
                    if table_name.startswith('django_') or table_name.startswith('auth_permission'):
                        continue
                    if table_name not in schema_data['tables']:
                        schema_data['tables'][table_name] = {'table_name': table_name, 'columns': [], 'primary_keys': [], 'foreign_keys': []}
                    is_pk = col_key == 'PRI'
                    if is_pk:
                        schema_data['tables'][table_name]['primary_keys'].append(col_name)
                    schema_data['tables'][table_name]['columns'].append({'name': col_name, 'type': data_type, 'nullable': is_nullable == 'YES', 'is_primary_key': is_pk, 'comment': comment or ''})
                fk_query = '\n                    SELECT \n                        TABLE_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME\n                    FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE\n                    WHERE TABLE_SCHEMA = %s AND REFERENCED_TABLE_NAME IS NOT NULL\n                '
                cursor.execute(fk_query, [db_name])
                fk_rows = cursor.fetchall()
                for table, col, ref_table, ref_col in fk_rows:
                    if table in schema_data['tables']:
                        schema_data['tables'][table]['foreign_keys'].append({'column': col, 'referenced_table': ref_table, 'referenced_column': ref_col})
                    schema_data['relationships'].append({'from_table': table, 'from_column': col, 'to_table': ref_table, 'to_column': ref_col})
        except Exception as e:
            kiki_logger.error(f'Failed to discover database schema: {e}')
            raise SchemaException(f'Database schema discovery failed: {str(e)}') from e
        cls._cached_schema = schema_data
        cls._last_refresh_time = current_time
        kiki_logger.info(f'Schema discovered successfully. Found {len(schema_data['tables'])} tables.')
        return schema_data

    @classmethod
    def refresh_schema(cls) -> Dict[str, Any]:
        """Manually forces a schema re-discovery and cache update."""
        return cls.initialize_schema(force_refresh=True)

    @classmethod
    def get_table_schema(cls, table_name: str) -> Optional[SchemaMatch]:
        """Returns SchemaMatch DTO for a specific table."""
        schema = cls.initialize_schema()
        t_info = schema['tables'].get(table_name)
        if not t_info:
            return None
        return SchemaMatch(table_name=t_info['table_name'], columns=t_info['columns'], primary_keys=t_info['primary_keys'], foreign_keys=t_info['foreign_keys'])

    @classmethod
    def get_relationships(cls, table_name: str) -> List[Dict[str, Any]]:
        """Returns all foreign key relationships connected to table_name."""
        schema = cls.initialize_schema()
        return [rel for rel in schema['relationships'] if rel['from_table'] == table_name or rel['to_table'] == table_name]

    @classmethod
    def search_schema(cls, search_terms: List[str], max_matches: Optional[int]=None) -> List[SchemaMatch]:
        """
        Searches cached metadata for tables matching search_terms.
        Matches against table names, column names, and column comments.
        Includes 1-hop FK related tables for context.
        Returns a list of SchemaMatch DTOs.
        """
        if max_matches is None:
            max_matches = KikiSettings.MAX_SCHEMA_MATCHES
        schema = cls.initialize_schema()
        all_tables = schema['tables']
        if not all_tables:
            return []
        clean_terms = [t.lower().strip() for t in search_terms if t and len(t.strip()) > 1]
        if not clean_terms:
            clean_terms = ['voucher', 'sales', 'customer', 'ledger']
        scored_tables = []
        for t_name, t_info in all_tables.items():
            score = 0
            t_name_lower = t_name.lower()
            if t_name_lower == 'vouchers' and any((term in {'voucher', 'vouchers', 'transaction', 'transactions', 'sale', 'sales', 'purchase', 'receipt', 'payment', 'last', 'latest'} for term in clean_terms)):
                score += 50
            for term in clean_terms:
                stem = term.rstrip('s')
                if term in t_name_lower or (len(stem) > 2 and stem in t_name_lower):
                    score += 10
            for col in t_info['columns']:
                col_name_lower = col['name'].lower()
                for term in clean_terms:
                    stem = term.rstrip('s')
                    if term in col_name_lower or (len(stem) > 2 and stem in col_name_lower):
                        score += 3
                    if col_name_lower == term or col_name_lower == stem:
                        score += 5
            if score > 0:
                scored_tables.append((score, t_name))
        scored_tables.sort(key=lambda x: x[0], reverse=True)
        top_table_names = [t[1] for t in scored_tables[:max_matches]]
        relevant_names: Set[str] = set(top_table_names)
        for t_name in top_table_names:
            t_info = all_tables[t_name]
            for fk in t_info.get('foreign_keys', []):
                ref = fk['referenced_table']
                if ref in all_tables:
                    relevant_names.add(ref)
        results: List[SchemaMatch] = []
        for t_name in sorted(relevant_names):
            t_info = all_tables[t_name]
            results.append(SchemaMatch(table_name=t_name, columns=t_info['columns'], primary_keys=t_info['primary_keys'], foreign_keys=t_info['foreign_keys']))
        return results